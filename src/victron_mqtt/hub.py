"""Module to communicate with the Venus OS MQTT Broker."""

import asyncio
import json
import logging
import ssl
from typing import Any, Optional

import paho.mqtt.client as mqtt
from paho.mqtt.client import Client as MQTTClient
from paho.mqtt.enums import CallbackAPIVersion

from victron_mqtt._topic_map import topic_map
from victron_mqtt.constants import TOPIC_INSTALLATION_ID, DeviceType
from victron_mqtt.data_classes import ParsedTopic
from victron_mqtt.device import Device
from victron_mqtt.metric import Metric

_LOGGER = logging.getLogger(__name__)

class Hub:
    """Class to communicate with the Venus OS hub."""

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        use_ssl: bool,
        installation_id: str | None = None,
        model_name: str | None = None,
        serial: str = "noserial",
    ) -> None:
        """Initialize."""
        _LOGGER.debug(
            "Initializing Hub(host=%s, port=%d, username=%s, use_ssl=%s, installation_id=%s, model_name=%s)",
            host, port, username, use_ssl, installation_id, model_name
        )
        self._model_name = model_name
        self.host = host
        self.username = username
        self.password = password
        self.serial = serial
        self.use_ssl = use_ssl
        self._client = None
        self.port = port
        self._installation_id = installation_id
        self.logger = logging.getLogger(__name__)
        self._devices: dict[str, Device] = {}
        self._first_refresh_event: asyncio.Event = asyncio.Event()
        self._installation_id_event: asyncio.Event = asyncio.Event()
        self._snapshot = {}
        self._keep_alive_task = None
        self._connected_event = asyncio.Event()
        _LOGGER.debug("Hub initialized")

    async def connect(self) -> None:
        """Connect to the hub."""
        _LOGGER.debug("Connecting to MQTT broker at %s:%d", self.host, self.port)
        self._client = MQTTClient(callback_api_version=CallbackAPIVersion.VERSION2)
        
        if self.username not in {None, ""}:
            _LOGGER.debug("Setting auth credentials for user: %s", self.username)
            self._client.username_pw_set(self.username, self.password)
        
        if self.use_ssl:
            _LOGGER.debug("Setting up SSL context")
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.VerifyMode.CERT_NONE
            self._client.tls_set_context(ssl_context)
            
        self._client.on_connect = self._on_connect
        self._client._on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message_callback
        
        try:
            self._client.connect_async(self.host, self.port)
            self._client.loop_start()
            await self._connected_event.wait()
            _LOGGER.info("Successfully connected to MQTT broker at %s:%d", self.host, self.port)
            if self._installation_id is None:
                _LOGGER.debug("No installation ID provided, attempting to read from device")
                self._installation_id = await self._read_installation_id()
            self._start_keep_alive_loop()
            await self._wait_for_first_refresh()
            _LOGGER.info("Devices and metrics initialized. Found %d devices", len(self._devices))
        except Exception as exc:
            _LOGGER.error("Failed to connect to MQTT broker: %s", exc)
            raise ConnectionError(f"Failed to connect to MQTT broker: {exc}") from exc

    def _on_connect(self, client: MQTTClient, userdata: Any, flags: dict, rc: int, properties: Optional[dict] = None) -> None:
        """Handle connection callback."""
        if rc == 0:
            _LOGGER.info("Connected to MQTT broker successfully")
            self._setup_subscriptions()
            self._connected_event.set()
        else:
            _LOGGER.error("Failed to connect with error code: %s. flags: %s", rc, flags)

    def _on_disconnect(self, client, userdata: Any, disconnect_flags: dict, reason_code, properties: Optional[dict] = None) -> None:
        """Handle disconnection callback."""
        if reason_code != 0:
            _LOGGER.warning("Unexpected disconnection from MQTT broker. Error: %s. flags: %s, Reconnecting...", reason_code, disconnect_flags)
        else:
            _LOGGER.info("Disconnected from MQTT broker.")

    def _on_message_callback(self, client: MQTTClient, userdata: Any, message: mqtt.MQTTMessage) -> None:
        """Process MQTT message asynchronously."""
        topic = message.topic
        payload = message.payload
        
        if "full_publish_completed" in topic:
            _LOGGER.info("Full publish completed, unsubscribing from notification")
            if self._client is not None and self._client.is_connected():
                self._client.unsubscribe("N/+/full_publish_completed")
            self._first_refresh_event.set()
            return

        if not self._installation_id_event.is_set():
            self._handle_installation_id_message(topic, payload)
            return

        self._handle_normal_message(topic, payload)

    def _handle_installation_id_message(self, topic: str, payload: bytes) -> None:
        """Handle installation ID message."""
        topic_parts = topic.split("/")
        if len(topic_parts) == 5 and topic_parts[2:5] == ["system", "0", "Serial"]:
            payload_json = json.loads(payload.decode())
            self._installation_id = payload_json.get("value")
            _LOGGER.info("Installation ID received: %s", self._installation_id)
            if self._installation_id_event:
                self._installation_id_event.set()

    def _handle_normal_message(self, topic: str, payload: bytes) -> None:
        """Handle regular MQTT message."""
        parsed_topic = ParsedTopic.from_topic(topic)
        if parsed_topic is None:
            _LOGGER.debug("Ignoring message - could not parse topic: %s", topic)
            return

        desc = topic_map.get(parsed_topic.wildcards_with_device_type)
        if desc is None:
            desc = topic_map.get(parsed_topic.wildcards_without_device_type)

        if desc is None:
            _LOGGER.debug("Ignoring message - no descriptor found for topic: %s", topic)
            return

        device = self._get_or_create_device(parsed_topic, desc)
        device.handle_message(parsed_topic, desc, payload.decode())

    async def disconnect(self) -> None:
        """Disconnect from the hub."""
        _LOGGER.debug("Disconnecting from MQTT broker")
        self._stop_keep_alive_loop()
        if self._client is None:
            _LOGGER.debug("No client to disconnect")
            return
        if self._client.is_connected():
            self._client.disconnect()
            _LOGGER.info("Disconnected from MQTT broker")
        self._client = None

    async def _keep_alive(self) -> None:
        """Send a keep alive message to the hub. Updates will only be made to the metrics
        for the 60 seconds following this method call."""
        # cspell:disable-next-line
        keep_alive_topic = f"R/{self._installation_id}/keepalive"

        if self._client is None:
            _LOGGER.warning("Cannot send keepalive - no MQTT client")
            return
        if not self._client.is_connected():
            _LOGGER.warning("Cannot send keepalive - client is not connected")
            return
        _LOGGER.debug("Sending keepalive message to topic: %s", keep_alive_topic)
        self._client.publish(keep_alive_topic, b"1")

    async def _keep_alive_loop(self) -> None:
        """Run keep_alive every 30 seconds."""
        _LOGGER.debug("Starting keepalive loop")
        while True:
            try:
                await self._keep_alive()
                await asyncio.sleep(30)
            except Exception as exc:
                _LOGGER.error("Error in keepalive loop: %s", exc, exc_info=True)
                await asyncio.sleep(5)  # Short delay before retrying

    def _start_keep_alive_loop(self) -> None:
        """Start the keep_alive loop."""
        _LOGGER.debug("Creating keepalive task")
        if self._keep_alive_task is None or self._keep_alive_task.done():
            self._keep_alive_task = asyncio.create_task(self._keep_alive_loop())
        else:
            _LOGGER.warning("Keepalive task already running")

    def _stop_keep_alive_loop(self) -> None:
        """Stop the keep_alive loop."""
        if self._keep_alive_task is not None:
            _LOGGER.debug("Cancelling keepalive task")
            self._keep_alive_task.cancel()
            self._keep_alive_task = None


    async def create_full_raw_snapshot(self) -> dict:
        """Create a full raw snapshot of the current state of the Venus OS device.
        Should not be used in conjunction with initialize_devices_and_metrics()."""
        _LOGGER.info("Creating full raw snapshot of device state")
        self._snapshot = {}
        if self._installation_id is None:
            _LOGGER.debug("No installation ID, reading from device")
            self._installation_id = await self._read_installation_id()
        assert self._client is not None
        self._client.on_message = self._on_snapshot_message
        self._client.subscribe("#")
        _LOGGER.debug("Subscribed to all topics for snapshot")
        await self._keep_alive()
        await self._wait_for_first_refresh()
        _LOGGER.info("Snapshot complete with %d top-level entries", len(self._snapshot))
        return self._snapshot

    def _set_nested_dict_value(self, d: dict, keys: list[str], value: str) -> None:
        for key in keys[:-1]:
            d = d.setdefault(key, {})
        d[keys[-1]] = value

    def _on_snapshot_message(
        self,
        client: MQTTClient,
        userdata: Any,
        message: mqtt.MQTTMessage,
    ) -> None:
        """Handle snapshot messages synchronously."""
        try:
            if "full_publish_completed" in message.topic:
                _LOGGER.info("Full publish completed, unsubscribing from notification")
                if self._client is not None:
                    self._client.unsubscribe("N/+/full_publish_completed")
                self._first_refresh_event.set()
                return

            topic_parts = message.topic.split("/")
            value = json.loads(message.payload.decode())
            self._set_nested_dict_value(self._snapshot, topic_parts, value)
        except Exception as exc:
            _LOGGER.error("Error processing snapshot message: %s", exc)

    def _on_installation_id_message(
        self,
        client: MQTTClient,
        userdata: Any,
        message: mqtt.MQTTMessage,
    ) -> None:
        """Handle installation ID messages synchronously."""
        try:
            topic_parts = message.topic.split("/")
            if len(topic_parts) == 5 and topic_parts[2:5] == ["system", "0", "Serial"]:
                payload_json = json.loads(message.payload.decode())
                self._installation_id = payload_json.get("value")
                _LOGGER.info("Installation ID received: %s", self._installation_id)
                if self._installation_id_event is not None:
                    self._installation_id_event.set()
        except Exception as exc:
            _LOGGER.error("Error processing installation ID message: %s", exc)

    async def _read_installation_id(self) -> str:
        """Read the installation id for the Victron installation."""
        _LOGGER.debug("Reading installation ID")
        if self._client is None:
            _LOGGER.error("Cannot read installation ID - no MQTT client")
            raise ProgrammingError
        if not self._client.is_connected():
            _LOGGER.error("Cannot read installation ID - client not connected")
            raise NotConnectedError

        self._client.subscribe(TOPIC_INSTALLATION_ID)
        try:
            await asyncio.wait_for(self._installation_id_event.wait(), timeout=60)
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout waiting for installation ID")
            raise
        if self._client is not None:
            self._client.unsubscribe(TOPIC_INSTALLATION_ID)
        _LOGGER.debug("Installation ID read successfully: %s", self.installation_id)
        return str(self.installation_id)

    def _setup_subscriptions(self) -> None:
        """Subscribe to list of topics."""
        _LOGGER.debug("Setting up MQTT subscriptions")
        if self._client is None:
            raise ProgrammingError
        if not self._client.is_connected():
            raise NotConnectedError

        _LOGGER.debug("Subscribing to topic map topics")
        for topic in topic_map:
            self._client.subscribe(topic)
            _LOGGER.debug("Subscribed to: %s", topic)

        self._client.subscribe("N/+/full_publish_completed")
        _LOGGER.debug("Subscribed to full_publish_completed notification")

    async def _wait_for_first_refresh(self) -> None:
        """Wait for the first full refresh to complete."""
        await asyncio.wait_for(self._first_refresh_event.wait(), timeout=60)

    def _get_or_create_device(self, parsed_topic: ParsedTopic, desc: Any) -> Device:
        """Get or create a device based on topic."""
        unique_id = self._create_device_unique_id(
            parsed_topic.installation_id,
            str(parsed_topic.device_type),
            parsed_topic.device_id,
        )
        device = self._devices.get(unique_id)
        if device is None:
            _LOGGER.info(
                "Creating new device: unique_id=%s, type=%s, id=%s",
                unique_id, parsed_topic.device_type, parsed_topic.device_id
            )
            device = Device(
                unique_id,
                desc,
                parsed_topic.installation_id,
                str(parsed_topic.device_type),
                parsed_topic.device_id,
            )
            self._devices[unique_id] = device
        return device

    def _create_device_unique_id(self, installation_id: str, device_type: str, device_id: str) -> str:
        """Create a unique ID for a device."""
        unique_id = f"{installation_id}_{device_type}_{device_id}"
        _LOGGER.debug("Created device unique ID: %s", unique_id)
        return unique_id

    def get_device_from_unique_id(self, unique_id: str) -> Device:
        """Get a device from a unique id."""
        device = self._devices.get(unique_id)
        if device is None:
            raise KeyError(f"Device with unique id {unique_id} not found.")
        return device

    def _get_device_unique_id_from_metric_unique_id(self, unique_id: str) -> str:
        return "_".join(unique_id.split("_")[:3])

    def get_metric_from_unique_id(self, unique_id: str) -> Metric | None:
        """Get a metric from a unique id."""
        device = self.get_device_from_unique_id(self._get_device_unique_id_from_metric_unique_id(unique_id))
        return device.get_metric_from_unique_id(unique_id)

    @property
    def devices(self) -> list[Device]:
        "Return a list of devices attached to the hub. Requires initialize_devices_and_metrics() to be called first."
        return list(self._devices.values())

    @property
    def installation_id(self) -> str | None:
        """Return the installation id."""
        return self._installation_id

    @property
    def model_name(self) -> str | None:
        """Return the model name."""
        return self._model_name

    @property
    def connected(self) -> bool:
        """Return if connected."""
        if self._client is None:
            return False
        return self._client.is_connected()


class ProgrammingError(Exception):
    """Error to indicate that we are in a state that should never be reached."""


class NotConnectedError(Exception):
    """Error to indicate that we expected to be connected at this stage but is not."""
