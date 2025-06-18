"""Module to communicate with the Venus OS MQTT Broker."""

import asyncio
import json
import logging

from gmqtt import Client as gmqttClient
from gmqtt.mqtt.handler import MQTTConnectError

from victron_mqtt._topic_map import topic_map
from victron_mqtt.constants import TOPIC_INSTALLATION_ID
from victron_mqtt.data_classes import ParsedTopic, TopicDescriptor
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
        self._first_refresh_event = asyncio.Event()
        self._installation_id_event: asyncio.Event | None = None
        self._snapshot = {}
        self._keep_alive_task = None
        _LOGGER.debug("Hub initialized")

    async def connect(self) -> None:
        """Connect to the hub."""
        _LOGGER.debug("Connecting to MQTT broker at %s:%d", self.host, self.port)
        self._client = gmqttClient("python-victron-venus")
        if self.username not in {None, ""}:
            _LOGGER.debug("Setting auth credentials for user: %s", self.username)
            self._client.set_auth_credentials(self.username, self.password)
        await self._client.connect(host=self.host, port=self.port, ssl=self.use_ssl)
        _LOGGER.info("Successfully connected to MQTT broker at %s:%d", self.host, self.port)

    async def initialize_devices_and_metrics(self) -> None:
        """Initialize devices and all the metrics."""
        _LOGGER.debug("Initializing devices and metrics")
        if self._installation_id is None:
            _LOGGER.debug("No installation ID provided, attempting to read from device")
            self._installation_id = await self._read_installation_id()
        await self._setup_subscriptions()
        self._start_keep_alive_loop()
        await self._wait_for_first_refresh()
        _LOGGER.info("Devices and metrics initialized. Found %d devices", len(self._devices))

    async def disconnect(self) -> None:
        """Disconnect from the hub."""
        _LOGGER.debug("Disconnecting from MQTT broker")
        self._stop_keep_alive_loop()
        if self._client is None:
            _LOGGER.debug("No client to disconnect")
            return
        if self._client.is_connected:
            await self._client.disconnect()
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
        if not self._client.is_connected:
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

    async def _on_snapshot_message(
        self,
        client: gmqttClient,
        topic: str,
        payload: bytes,
        qos: int,
        retain: bool,  # pylint: disable=unused-argument
    ) -> None:
        _LOGGER.debug("Processing snapshot message: topic=%s", topic)
        topic_parts = topic.split("/")
        value = json.loads(payload.decode())
        self._set_nested_dict_value(self._snapshot, topic_parts, value)
        if "full_publish_completed" in topic:
            _LOGGER.info("Full snapshot completed")
            self._first_refresh_event.set()

    async def _on_installation_id_message(
        self,
        client: gmqttClient,
        topic: str,
        payload: bytes,
        qos: int,
        retain: bool,  # pylint: disable=unused-argument
    ) -> None:
        """Handle an incoming message from the hub."""
        _LOGGER.debug("Processing installation ID message: topic=%s", topic)
        topic_parts = topic.split("/")

        if len(topic_parts) != 5:
            _LOGGER.debug("Ignoring message - unexpected topic structure")
            return

        if topic_parts[2] == "system" and topic_parts[3] == "0" and topic_parts[4] == "Serial":
            payload_json = json.loads(payload.decode())
            self._installation_id = payload_json.get("value")
            _LOGGER.info("Installation ID received: %s", self._installation_id)
            assert self._installation_id_event is not None
            self._installation_id_event.set()

    async def _read_installation_id(self) -> str:
        """Read the installation id for the Victron installation. Depends on no other
        subscriptions being active."""
        _LOGGER.debug("Reading installation ID")
        if self._client is None:
            _LOGGER.error("Cannot read installation ID - no MQTT client")
            raise ProgrammingError
        if not self._client.is_connected:
            _LOGGER.error("Cannot read installation ID - client not connected")
            raise NotConnectedError

        self._client.on_message = self._on_installation_id_message
        self._installation_id_event = asyncio.Event()
        self._client.subscribe(TOPIC_INSTALLATION_ID)
        try:
            await asyncio.wait_for(self._installation_id_event.wait(), timeout=60)
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout waiting for installation ID")
            raise
        self._client.unsubscribe(TOPIC_INSTALLATION_ID)
        _LOGGER.debug("Installation ID read successfully: %s", self.installation_id)
        return str(self.installation_id)

    async def verify_connection_details(self) -> str:
        """Verify the username and password. This method connects and disconnects
        from the Venus OS device. Do not call connect() before this method."""
        _LOGGER.debug("Verifying connection details")
        try:
            await self.connect()
            installation_id = await self._read_installation_id()
            _LOGGER.info("Connection details verified successfully")
            return installation_id
        except MQTTConnectError as e:
            if "135" in str(e):
                _LOGGER.error("Authentication failed")
                raise InvalidAuthError from e
            _LOGGER.error("Connection failed: %s", str(e))
            raise CannotConnectError from e
        finally:
            await self.disconnect()

    async def _setup_subscriptions(self) -> None:
        """Subscribe to list of topics."""
        _LOGGER.debug("Setting up MQTT subscriptions")
        if self._client is None:
            raise ProgrammingError
        if not self._client.is_connected:
            raise NotConnectedError

        self._client.on_message = self._on_message
        
        _LOGGER.debug("Subscribing to topic map topics")
        for topic in topic_map:
            self._client.subscribe(topic)
            _LOGGER.debug("Subscribed to: %s", topic)

        self._client.subscribe("N/+/full_publish_completed")
        _LOGGER.debug("Subscribed to full_publish_completed notification")

    async def _wait_for_first_refresh(self) -> None:
        """Wait for the first full refresh to complete, as per the
        "full_publish_completed" MQTT message."""
        await asyncio.wait_for(self._first_refresh_event.wait(), timeout=60)

    def _create_device_unique_id(self, installation_id: str, device_type: str, device_id: str) -> str:
        unique_id = f"{installation_id}_{device_type}_{device_id}"
        _LOGGER.debug("Created device unique ID: %s", unique_id)
        return unique_id

    def _get_or_create_device(self, parsed_topic: ParsedTopic, desc: TopicDescriptor) -> Device:
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
            if parsed_topic.device_type == "system":
                name = self.model_name if self.model_name is not None else "Victron Venus"
                _LOGGER.debug("Setting root device name to: %s", name)
                device.set_root_device_name(name)

        return device

    async def _on_message(
        self,
        client: gmqttClient,
        topic: str,
        payload: bytes,
        qos: int,
        retain: bool,  # noqa:  ARG002 pylint: disable=unused-argument
    ) -> None:
        """Handle an incoming message from the hub."""
        _LOGGER.debug("Message received: topic=%s, qos=%d, retain=%s", topic, qos, retain)

        if "full_publish_completed" in topic:
            _LOGGER.info("Full publish completed, unsubscribing from notification")
            client.unsubscribe("N/+/full_publish_completed")
            self._first_refresh_event.set()
            return

        parsed_topic = ParsedTopic.from_topic(topic)
        if parsed_topic is None:
            _LOGGER.debug("Ignoring message - could not parse topic: %s", topic)
            return

        if parsed_topic.device_type != "system" and parsed_topic.device_id == "0":
            _LOGGER.debug("Ignoring message - device_id=0 for non-system device")
            return

        desc = topic_map.get(parsed_topic.wildcards_with_device_type)
        if desc is None:
            desc = topic_map.get(parsed_topic.wildcards_without_device_type)

        if desc is None:
            _LOGGER.debug("Ignoring message - no descriptor found for topic: %s", topic)
            return

        device = self._get_or_create_device(parsed_topic, desc)
        await device.handle_message(parsed_topic, desc, payload.decode())

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
        return self._client.is_connected


class CannotConnectError(Exception):
    """Error to indicate we cannot connect."""


class InvalidAuthError(Exception):
    """Error to indicate there is invalid auth."""


class ProgrammingError(Exception):
    """Error to indicate that we are in a state that should never be reached."""


class NotConnectedError(Exception):
    """Error to indicate that we expected to be connected at this stage but is not."""
