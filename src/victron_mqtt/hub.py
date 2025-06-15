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


class Hub:
    """Class to communicate with the Venus OS hub."""

    _installation_id_event: asyncio.Event

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        use_ssl: bool,
        installation_id: str = None,
        model_name: str = None,
        serial: str = "noserial",
    ) -> None:
        """Initialize."""
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
        self._installation_id_event = None
        self._snapshot = {}
        self._keep_alive_task = None

    async def connect(self) -> None:
        """Connect to the hub."""
        self._client = gmqttClient("python-victron-venus")
        if self.username not in {None, ""}:
            self._client.set_auth_credentials(self.username, self.password)
        await self._client.connect(host=self.host, port=self.port, ssl=self.use_ssl)

    async def initialize_devices_and_metrics(self) -> None:
        """Initialize devices and all the metrics."""
        if self._installation_id is None:
            self._installation_id = await self._read_installation_id()
        await self._setup_subscriptions()
        self._start_keep_alive_loop()
        await self._wait_for_first_refresh()

    async def disconnect(self) -> None:
        """Disconnect from the hub."""
        self._stop_keep_alive_loop()
        if self._client is None:
            return
        if self._client.is_connected:
            await self._client.disconnect()
        self._client = None

    

    async def _keep_alive(self) -> None:
        """Send a keep alive message to the hub. Updates will only be made to the metrics
        for the 60 seconds following this method call."""
        # cspell:disable-next-line
        keep_alive_topic = f"R/{self._installation_id}/keepalive"

        if self._client is not None:
            if self._client.is_connected:
                self._client.publish(keep_alive_topic, b"1")


    async def _keep_alive_loop(self) -> None:
        """Run keep_alive every 30 seconds."""
        while True:
            await self._keep_alive()
            await asyncio.sleep(30)

    def _start_keep_alive_loop(self) -> None:
        """Start the keep_alive loop."""
        if self._keep_alive_task is None or self._keep_alive_task.done():
            self._keep_alive_task = asyncio.create_task(self._keep_alive_loop())

    def _stop_keep_alive_loop(self) -> None:
        """Stop the keep_alive loop."""
        if self._keep_alive_task is not None:
            self._keep_alive_task.cancel()
            self._keep_alive_task = None


    async def create_full_raw_snapshot(self) -> dict:
        """Create a full raw snapshot of the current state of the Venus OS device.
        Should not be used in conjunction with initialize_devices_and_metrics()."""
        self._snapshot = {}
        if self._installation_id is None:
            self._installation_id = await self._read_installation_id()
        self._client.on_message = self._on_snapshot_message
        self._client.subscribe("#")
        await self._keep_alive()
        await self._wait_for_first_refresh()
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
        topic_parts = topic.split("/")
        value = json.loads(payload.decode())
        self._set_nested_dict_value(self._snapshot, topic_parts, value)
        if "full_publish_completed" in topic:
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

        topic_parts = topic.split("/")

        if len(topic_parts) != 5:
            return

        if topic_parts[2] == "system" and topic_parts[3] == "0" and topic_parts[4] == "Serial":
            payload_json = json.loads(payload.decode())
            self._installation_id = payload_json.get("value")
            self._installation_id_event.set()

    async def _read_installation_id(self) -> str:
        """Read the installation id for the Victron installation. Depends on no other
        subscriptions being active."""

        if self._client is None:
            raise ProgrammingError
        if not self._client.is_connected:
            raise NotConnectedError
        self._client.on_message = self._on_installation_id_message
        self._installation_id_event = asyncio.Event()
        self._client.subscribe(TOPIC_INSTALLATION_ID)
        await asyncio.wait_for(self._installation_id_event.wait(), timeout=60)
        self._client.unsubscribe(TOPIC_INSTALLATION_ID)
        return str(self.installation_id)

    async def verify_connection_details(self) -> str:
        """Verify the username and password. This method connects and disconnects
        from the Venus OS device. Do not call connect() before this method."""

        try:
            await self.connect()
            return await self._read_installation_id()
        except MQTTConnectError as e:
            if "135" in str(e):
                raise InvalidAuthError from e
            raise CannotConnectError from e
        finally:
            await self.disconnect()

    async def _setup_subscriptions(self) -> None:
        """Subscribe to list of topics."""

        if self._client is None:
            raise ProgrammingError
        if not self._client.is_connected:
            raise NotConnectedError

        self._client.on_message = self._on_message

        for topic in topic_map:
            self._client.subscribe(topic)

        self._client.subscribe("N/+/full_publish_completed")

    async def _wait_for_first_refresh(self) -> None:
        """Wait for the first full refresh to complete, as per the
        "full_publish_completed" MQTT message."""
        await asyncio.wait_for(self._first_refresh_event.wait(), timeout=60)

    def _create_device_unique_id(self, installation_id: str, device_type: str, device_id: str) -> str:
        return f"{installation_id}_{device_type}_{device_id}"

    def _get_or_create_device(self, parsed_topic: ParsedTopic, desc: TopicDescriptor) -> Device:
        unique_id = self._create_device_unique_id(
            parsed_topic.installation_id,
            parsed_topic.device_type,
            parsed_topic.device_id,
        )
        device = self._devices.get(unique_id)
        if device is None:
            device = Device(
                unique_id,
                desc,
                parsed_topic.installation_id,
                parsed_topic.device_type,
                parsed_topic.device_id,
            )
            self._devices[unique_id] = device
            if parsed_topic.device_type == "system":
                if self.model_name is not None:
                    device.set_root_device_name(self._model_name)
                else:
                    device.set_root_device_name("Victron Venus")

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

        if "full_publish_completed" in topic:
            client.unsubscribe("N/+/full_publish_completed")
            self._first_refresh_event.set()
            return

        parsed_topic = ParsedTopic.from_topic(topic)
        if parsed_topic is None:
            return

        if parsed_topic.device_type != "system" and parsed_topic.device_id == "0":
            return

        desc = topic_map.get(parsed_topic.wildcards_with_device_type)
        if desc is None:
            desc = topic_map.get(parsed_topic.wildcards_without_device_type)

        if desc is None:
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

    def get_metric_from_unique_id(self, unique_id: str) -> Metric:
        """Get a metric from a unique id."""
        device = self.get_device_from_unique_id(self._get_device_unique_id_from_metric_unique_id(unique_id))
        return device.get_metric_from_unique_id(unique_id)

    @property
    def devices(self) -> list[Device]:
        "Return a list of devices attached to the hub. Requires initialize_devices_and_metrics() to be called first."
        return list(self._devices.values())

    @property
    def installation_id(self) -> str:
        """Return the installation id."""
        return self._installation_id

    @property
    def model_name(self) -> str:
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
