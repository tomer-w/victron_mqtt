"""Module to communicate with the Venus OS MQTT Broker."""

import asyncio
import json
import logging
import ssl
import re
from typing import Any, Optional

import paho.mqtt.client as mqtt
from paho.mqtt.client import Client as MQTTClient, PayloadType
from paho.mqtt.enums import CallbackAPIVersion
from paho.mqtt.reasoncodes import ReasonCode
from paho.mqtt.properties import Properties

from ._victron_topics import topics
from .constants import TOPIC_INSTALLATION_ID
from .data_classes import ParsedTopic, TopicDescriptor
from .device import Device
from .metric import Metric

_LOGGER = logging.getLogger(__name__)

# Modify the logger to include instance_id without changing the tracing level
class InstanceIDFilter(logging.Filter):
    def __init__(self, instance_id):
        super().__init__()
        self.instance_id = instance_id

    def filter(self, record):
        record.instance_id = self.instance_id
        return True

# Update the log format to include instance_id
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - [ID: %(instance_id)s] - %(message)s')
for handler in logging.getLogger().handlers:
    handler.setFormatter(formatter)

# class TracedTask(asyncio.Task):
#     def __init__(self, coro, *, loop=None, name=None):
#         super().__init__(coro, loop=loop, name=name)
#         print(f"[TASK START] {self.get_name()} - {coro}")
#         self.add_done_callback(self._on_done)

#     def _on_done(self, fut):
#         try:
#             result = fut.result()
#         except Exception as e:
#             print(f"[TASK ERROR] {self.get_name()} - {e}")
#         else:
#             print(f"[TASK DONE] {self.get_name()} - Result: {result}")

running_client_id=0
class Hub:
    """Class to communicate with the Venus OS hub."""

    def __init__(
        self,
        host: str,
        port: int,
        username: str | None,
        password: str | None,
        use_ssl: bool,
        installation_id: str | None = None,
        model_name: str | None = None,
        serial: str | None = "noserial",
        topic_prefix: str | None = None,
        logger_level: int | None = None

    ) -> None:
        """Initialize."""
        global running_client_id
        self._instance_id = running_client_id
        running_client_id += 1

        # Add the instance_id filter to the logger only if it doesn't already exist
        self.logger = logging.getLogger(__name__)
        self.logger.addFilter(InstanceIDFilter(self._instance_id))
        if logger_level is not None:
            self.logger.setLevel(logger_level)

        # Parameter validation
        if not isinstance(host, str) or not host:
            raise ValueError("host must be a non-empty string")
        if not isinstance(port, int) or not (0 < port < 65536):
            raise ValueError("port must be an integer between 1 and 65535")
        if username is not None and not isinstance(username, str):
            raise TypeError(f"username must be a string or None, got type={type(username).__name__}, value={username!r}")
        if password is not None and not isinstance(password, str):
            raise TypeError(f"password must be a string or None, got type={type(password).__name__}, value={password!r}")
        if not isinstance(use_ssl, bool):
            raise TypeError(f"use_ssl must be a boolean, got type={type(use_ssl).__name__}, value={use_ssl!r}")
        if installation_id is not None and not isinstance(installation_id, str):
            raise TypeError(f"installation_id must be a string or None, got type={type(installation_id).__name__}, value={installation_id!r}")
        if model_name is not None and not isinstance(model_name, str):
            raise TypeError(f"model_name must be a string or None, got type={type(model_name).__name__}, value={model_name!r}")
        if serial is not None and not isinstance(serial, str):
            raise TypeError(f"serial must be a string or None, got type={type(serial).__name__}, value={serial!r}")
        if topic_prefix is not None and not isinstance(topic_prefix, str):
            raise TypeError(f"topic_prefix must be a string or None, got type={type(topic_prefix).__name__}, value={topic_prefix!r}")
        _LOGGER.info(
            "Initializing Hub(host=%s, port=%d, username=%s, use_ssl=%s, installation_id=%s, model_name=%s, topic_prefix=%s)",
            host, port, username, use_ssl, installation_id, model_name, topic_prefix
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
        self._topic_prefix = topic_prefix
        self._devices: dict[str, Device] = {}
        self._first_refresh_event: asyncio.Event = asyncio.Event()
        self._installation_id_event: asyncio.Event = asyncio.Event()
        self._snapshot = {}
        self._keep_alive_task = None
        self._connected_event = asyncio.Event()
        self._connected_failed = False
        # Replace all {placeholder} patterns with + for MQTT wildcards
        expanded_topics = Hub.expand_topic_list(topics)
        def merge_is_adjustable_suffix(desc: TopicDescriptor) -> str:
            """Merge the topic with its adjustable suffix."""
            assert desc.is_adjustable_suffix is not None
            return Hub._remove_placeholders_map(desc.topic.rsplit('/', 1)[0] + '/' + desc.is_adjustable_suffix)

        # Helper to build a map where duplicate keys accumulate values in a list
        def build_multi_map(items, key_func):
            result = {}
            for item in items:
                key = key_func(item)
                if key in result:
                    existing = result[key]
                    existing.append(item)
                else:
                    result[key] = [item]
            return result

        self.topic_map = build_multi_map(expanded_topics, lambda desc: Hub._remove_placeholders_map(desc.topic))
        self.fallback_map = build_multi_map(
            [desc for desc in expanded_topics if desc.is_adjustable_suffix],
            lambda desc: Hub._remove_placeholders_map(merge_is_adjustable_suffix(desc))
        )
        subscription_list1 = [Hub._remove_placeholders(topic.topic) for topic in expanded_topics]
        subscription_list2 = [Hub._remove_placeholders(merge_is_adjustable_suffix(desc)) for desc in expanded_topics if desc.is_adjustable_suffix]
        self._subscription_list = subscription_list1 + subscription_list2
        self._client = MQTTClient(callback_api_version=CallbackAPIVersion.VERSION2, client_id="victron_mqtt-" + str(self._instance_id))
        _LOGGER.info("Hub initialized")

    async def connect(self) -> None:
        """Connect to the hub."""
        _LOGGER.info("Connecting to MQTT broker at %s:%d", self.host, self.port)
        
        if self.username is not None:
            _LOGGER.info("Setting auth credentials for user: %s", self.username)
            self._client.username_pw_set(self.username, self.password)
        
        if self.use_ssl:
            _LOGGER.info("Setting up SSL context")
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.VerifyMode.CERT_NONE
            self._client.tls_set_context(ssl_context)
            
        self._client.on_connect = self._on_connect
        self._client._on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        self._client.on_connect_fail = self.on_connect_fail
        #self._client.on_log = self._on_log
        self._connected_failed = False
        self._loop = asyncio.get_event_loop()
        #self._loop.set_task_factory(lambda loop, coro: TracedTask(coro, loop=loop))

        try:
            _LOGGER.info("Starting paho mqtt")
            self._client.loop_start()
            _LOGGER.info("Connecting")
            self._client.connect_async(self.host, self.port)
            _LOGGER.info("Waiting for connection event")
            await self._wait_for_connect()
            if self._connected_failed:
                _LOGGER.error("Failed to connect to MQTT broker")
                raise CannotConnectError("Failed to connect to MQTT broker")
            _LOGGER.info("Successfully connected to MQTT broker at %s:%d", self.host, self.port)
            if self._installation_id is None:
                _LOGGER.info("No installation ID provided, attempting to read from device")
                self._installation_id = await self._read_installation_id()
            self._start_keep_alive_loop()
            _LOGGER.info("Waiting for first refresh")
            await self._wait_for_first_refresh()
            _LOGGER.info("Devices and metrics initialized. Found %d devices", len(self._devices))
        except Exception as exc:
            _LOGGER.error("Failed to connect to MQTT broker: %s", exc, exc_info=True)
            raise CannotConnectError(f"Failed to connect to MQTT broker: {exc}") from exc

    def _on_log(self, client: MQTTClient, userdata: Any, level:int, buf:str) -> None:
        _LOGGER.log(level, buf)

    def _on_connect(self, client: MQTTClient, userdata: Any, flags: dict, rc: int, properties: Optional[dict] = None) -> None:
        try:
            self._on_connect_internal(client, userdata, flags, rc, properties)
        except Exception as exc:
            _LOGGER.exception("_on_connect exception %s: %s", type(exc), exc, exc_info=True)

    def _on_connect_internal(self, client: MQTTClient, userdata: Any, flags: dict, rc: int, properties: Optional[dict] = None) -> None:
        """Handle connection callback."""
        if self._client is None:
            _LOGGER.warning("Got new connection while self._client is None, ignoring")
            return
        if rc == 0:
            _LOGGER.info("Connected to MQTT broker successfully")
            self._setup_subscriptions()
            self._loop.call_soon_threadsafe(self._connected_event.set)
        else:
            _LOGGER.error("Failed to connect with error code: %s. flags: %s", rc, flags)

    def _on_disconnect(self, client: MQTTClient, userdata: Any, disconnect_flags: mqtt.DisconnectFlags, reason_code: ReasonCode, properties: Optional[Properties] = None) -> None:
        """Handle disconnection callback."""
        if reason_code != 0:
            _LOGGER.warning("Unexpected disconnection from MQTT broker. Error: %s. flags: %s, Reconnecting...", reason_code, disconnect_flags)
        else:
            _LOGGER.info("Disconnected from MQTT broker.")

    def _on_message(self, client: MQTTClient, userdata: Any, message: mqtt.MQTTMessage) -> None:
        try:
            self._on_message_internal(client, userdata, message)
        except Exception as exc:
            _LOGGER.exception("_on_message exception %s: %s", type(exc), exc, exc_info=True)

    def _on_message_internal(self, client: MQTTClient, userdata: Any, message: mqtt.MQTTMessage) -> None:
        """Process MQTT message asynchronously."""
        topic = message.topic
        payload = message.payload
        _LOGGER.debug("Message received: topic=%s, payload=%s", topic, payload)
        
        # Remove topic prefix before processing
        topic = self._remove_topic_prefix(topic)
        
        if "full_publish_completed" in topic:
            _LOGGER.info("Full publish completed, unsubscribing from notification")
            if self._client is not None and self._client.is_connected():
                self._unsubscribe("N/+/full_publish_completed")
            self._loop.call_soon_threadsafe(self._first_refresh_event.set)
            return

        if self._installation_id is None and not self._installation_id_event.is_set():
            self._handle_installation_id_message(topic, payload)
            return

        self._handle_normal_message(topic, payload)

    def _handle_installation_id_message(self, topic: str, payload: bytes) -> None:
        """Handle installation ID message."""
        parsed_topic = ParsedTopic.from_topic(topic)
        if parsed_topic is None:
            _LOGGER.debug("Ignoring message - could not parse topic: %s", topic)
            return
        
        self._installation_id = parsed_topic.installation_id
        _LOGGER.info("Installation ID received: %s. Original topic: %s", self._installation_id, topic)
        self._loop.call_soon_threadsafe(self._installation_id_event.set)

    def _handle_normal_message(self, topic: str, payload: bytes) -> None:
        """Handle regular MQTT message."""
        parsed_topic = ParsedTopic.from_topic(topic)
        if parsed_topic is None:
            _LOGGER.debug("Ignoring message - could not parse topic: %s", topic)
            return

        fallback_to_metric_topic: bool = False
        desc_list = self.topic_map.get(parsed_topic.wildcards_with_device_type)
        if desc_list is None:
            desc_list = self.topic_map.get(parsed_topic.wildcards_without_device_type)
        if desc_list is None:
            desc_list = self.fallback_map.get(parsed_topic.wildcards_with_device_type)
            fallback_to_metric_topic = True
        if desc_list is None:
            desc_list = self.fallback_map.get(parsed_topic.wildcards_without_device_type)
            fallback_to_metric_topic = True
        if desc_list is None:
            _LOGGER.debug("Ignoring message - no descriptor found for topic: %s", topic)
            return
        if len(desc_list) == 1:
            desc = desc_list[0]
        else:
            desc = parsed_topic.match_from_list(desc_list)
            if desc is None:
                _LOGGER.debug("Ignoring message - no matching descriptor found for list of topic: %s", topic)
                return

        device = self._get_or_create_device(parsed_topic, desc)
        device.handle_message(fallback_to_metric_topic, topic, parsed_topic, desc, payload.decode(), self._loop, self)

    async def disconnect(self) -> None:
        """Disconnect from the hub."""
        _LOGGER.info("Disconnecting from MQTT broker")
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
        keep_alive_topic = f"R/{self._installation_id}/keepalive"

        if self._client is None:
            _LOGGER.warning("Cannot send keepalive - no MQTT client")
            return
        if not self._client.is_connected():
            _LOGGER.warning("Cannot send keepalive - client is not connected")
            return
        _LOGGER.debug("Sending keepalive message to topic: %s", keep_alive_topic)
        self.publish(keep_alive_topic, b"1")

    def publish(self, topic: str, value: PayloadType) -> None:
        assert self._client is not None
        prefixed_topic = self._add_topic_prefix(topic)
        self._client.publish(prefixed_topic, value)

    async def _keep_alive_loop(self) -> None:
        """Run keep_alive every 30 seconds."""
        _LOGGER.info("Starting keepalive loop")
        try:
            while True:
                try:
                    await self._keep_alive()
                    await asyncio.sleep(30)
                except Exception as exc:
                    _LOGGER.error("Error in keepalive loop: %s", exc, exc_info=True)
                    await asyncio.sleep(5)  # Short delay before retrying
        except asyncio.CancelledError:
            _LOGGER.info("Keepalive loop canceled")
            raise

    def _start_keep_alive_loop(self) -> None:
        """Start the keep_alive loop."""
        _LOGGER.info("Creating keepalive task")
        if self._keep_alive_task is None or self._keep_alive_task.done():
            self._keep_alive_task = asyncio.create_task(self._keep_alive_loop())
        else:
            _LOGGER.warning("Keepalive task already running")

    def _stop_keep_alive_loop(self) -> None:
        """Stop the keep_alive loop."""
        if self._keep_alive_task is not None:
            _LOGGER.info("Cancelling keepalive task")
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
        self._first_refresh_event.clear()
        self._client.on_message = self._on_snapshot_message
        self._subscribe("#")
        _LOGGER.info("Subscribed to all topics for snapshot")
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
            topic = self._remove_topic_prefix(message.topic)
            if "full_publish_completed" in topic:
                _LOGGER.info("Full publish completed, unsubscribing from notification")
                if self._client is not None:
                    self._unsubscribe("N/+/full_publish_completed")
                self._loop.call_soon_threadsafe(self._first_refresh_event.set)
                return

            topic_parts = topic.split("/")
            value = json.loads(message.payload.decode())
            self._set_nested_dict_value(self._snapshot, topic_parts, value)
        except Exception as exc:
            _LOGGER.error("Error processing snapshot message: %s", exc, exc_info=True)

    def _on_installation_id_message(
        self,
        client: MQTTClient,
        userdata: Any,
        message: mqtt.MQTTMessage,
    ) -> None:
        """Handle installation ID messages synchronously."""
        try:
            topic = self._remove_topic_prefix(message.topic)
            topic_parts = topic.split("/")
            if len(topic_parts) == 5 and topic_parts[2:5] == ["system", "0", "Serial"]:
                payload_json = json.loads(message.payload.decode())
                self._installation_id = payload_json.get("value")
                _LOGGER.info("Installation ID received: %s", self._installation_id)
                if self._installation_id_event is not None:
                    self._loop.call_soon_threadsafe(self._installation_id_event.set)
        except Exception as exc:
            _LOGGER.error("Error processing installation ID message: %s", exc)

    async def _read_installation_id(self) -> str:
        """Read the installation id for the Victron installation."""
        _LOGGER.info("Reading installation ID")
        if self._client is None:
            _LOGGER.error("Cannot read installation ID - no MQTT client")
            raise ProgrammingError
        if not self._client.is_connected():
            _LOGGER.error("Cannot read installation ID - client not connected")
            raise NotConnectedError

        self._subscribe(TOPIC_INSTALLATION_ID)
        try:
            await asyncio.wait_for(self._installation_id_event.wait(), timeout=60)
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout waiting for installation ID")
            raise
        if self._client is not None:
            self._unsubscribe(TOPIC_INSTALLATION_ID)
        _LOGGER.info("Installation ID read successfully: %s", self.installation_id)
        return str(self.installation_id)

    @staticmethod
    def _remove_placeholders(topic: str) -> str:
        return re.sub(r'\{[^}]+\}', '+', topic)

    @staticmethod
    def _remove_placeholders_map(topic: str) -> str:
        topic_parts = topic.split("/")
        for i, part in enumerate(topic_parts):
            if part == "{phase}":
                topic_parts[i] = "##phase##"
            elif part.isdigit() or (part.startswith("{") and part.endswith("}")):
                topic_parts[i] = "##num##"
        return "/".join(topic_parts)

    def _add_topic_prefix(self, topic: str) -> str:
        """Add the topic prefix to a topic if configured."""
        if self._topic_prefix is None:
            return topic
        return f"{self._topic_prefix}/{topic}"

    def _remove_topic_prefix(self, topic: str) -> str:
        """Remove the topic prefix from a topic if configured."""
        if self._topic_prefix is None:
            return topic
        if topic.startswith(f"{self._topic_prefix}/"):
            return topic[len(self._topic_prefix) + 1:]
        return topic

    def _subscribe(self, topic: str) -> None:
        """Subscribe to a topic with automatic prefix handling."""
        assert self._client is not None
        prefixed_topic = self._add_topic_prefix(topic)
        _LOGGER.debug("Subscribing to: %s", prefixed_topic)
        self._client.subscribe(prefixed_topic)

    def _unsubscribe(self, topic: str) -> None:
        """Unsubscribe from a topic with automatic prefix handling."""
        assert self._client is not None
        prefixed_topic = self._add_topic_prefix(topic)
        self._client.unsubscribe(prefixed_topic)
        _LOGGER.debug("Unsubscribed from: %s", prefixed_topic)

    def _setup_subscriptions(self) -> None:
        """Subscribe to list of topics."""
        _LOGGER.info("Setting up MQTT subscriptions")
        assert self._client is not None
        if not self._client.is_connected():
            raise NotConnectedError
        #topic_list = [(topic, 0) for topic in topic_map]
        for topic in self._subscription_list:
            self._subscribe(topic)

        self._subscribe("N/+/full_publish_completed")
        _LOGGER.info("Subscribed to full_publish_completed notification")

    async def _wait_for_connect(self) -> None:
        """Wait for the first connection to complete."""
        try:
            await asyncio.wait_for(self._connected_event.wait(), timeout=25)
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout waiting for first first connection")
            raise CannotConnectError("Timeout waiting for first connection")

    async def _wait_for_first_refresh(self) -> None:
        """Wait for the first full refresh to complete."""
        try:
            await asyncio.wait_for(self._first_refresh_event.wait(), timeout=60)
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout waiting for first full refresh")
            raise CannotConnectError("Timeout waiting for first full refresh")

    def _get_or_create_device(self, parsed_topic: ParsedTopic, desc: TopicDescriptor) -> Device:
        """Get or create a device based on topic."""
        unique_id = self._create_device_unique_id(
            parsed_topic.installation_id,
            parsed_topic.device_type.code,
            parsed_topic.device_id,
        )
        device = self._devices.get(unique_id)
        if device is None:
            _LOGGER.info("Creating new device: unique_id=%s, parsed_topic=%s", unique_id, parsed_topic)
            device = Device(
                unique_id,
                parsed_topic,
                desc,
            )
            self._devices[unique_id] = device
        return device

    def _create_device_unique_id(self, installation_id: str, device_type: str, device_id: str) -> str:
        """Create a unique ID for a device."""
        unique_id = f"{installation_id}_{device_type}_{device_id}"
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
    def topic_prefix(self) -> str | None:
        """Return the topic prefix."""
        return self._topic_prefix

    @property
    def connected(self) -> bool:
        """Return if connected."""
        if self._client is None:
            return False
        return self._client.is_connected()

    def on_connect_fail(self, client: MQTTClient, userdata: Any) -> None:
        """Handle connection failure callback."""
        _LOGGER.error("Connection to MQTT broker failed")
        self._connected_failed = True
        self._loop.call_soon_threadsafe(self._connected_event.set)

    @staticmethod
    def expand_topic_list(topic_list: list[TopicDescriptor]) -> list[TopicDescriptor]:
        """
        Expands TopicDescriptors with placeholders like {output(1-4)} into multiple descriptors.
        """
        import re
        expanded = []
        pattern = re.compile(r"\{([a-zA-Z0-9_]+)\((\d+)-(\d+)\)\}")
        for td in topic_list:
            matches = list(pattern.finditer(td.topic))
            if matches:
                # For each placeholder, expand all combinations
                # Only support one placeholder per field for now
                match = matches[0]
                key, start, end = match.group(1), int(match.group(2)), int(match.group(3))
                for i in range(start, end+1):
                    new_kwargs = td.__dict__.copy()
                    new_kwargs['topic'] = pattern.sub(str(i), td.topic)
                    new_kwargs['key_values'] = {key: str(i)}
                    expanded.append(TopicDescriptor(**new_kwargs))
            else:
                expanded.append(td)
        return expanded



class CannotConnectError(Exception):
    """Error to indicate we cannot connect."""


class ProgrammingError(Exception):
    """Error to indicate that we are in a state that should never be reached."""


class NotConnectedError(Exception):
    """Error to indicate that we expected to be connected at this stage but is not."""
