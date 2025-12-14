"""Module to communicate with the Venus OS MQTT Broker."""

from dataclasses import replace
import asyncio
import copy
import json
import logging
import random
import ssl
import re
import string
from typing import Any, Callable, Optional, Tuple
import time

import paho.mqtt.client as mqtt
from paho.mqtt.client import Client as MQTTClient, PayloadType, ConnectFlags, connack_string
from paho.mqtt.enums import CallbackAPIVersion
from paho.mqtt.reasoncodes import ReasonCode
from paho.mqtt.properties import Properties

from .writable_metric import WritableMetric

from ._victron_topics import topics
from ._victron_enums import DeviceType
from .constants import TOPIC_INSTALLATION_ID, MetricKind, OperationMode
from .data_classes import ParsedTopic, TopicDescriptor, topic_to_device_type
from .device import Device, FallbackPlaceholder, MetricPlaceholder
from .metric import Metric
from .id_utils import reraise_same_exception

_LOGGER = logging.getLogger(__name__)
CONNECT_MAX_FAILED_ATTEMPTS = 3
FORCE_INVALIDATE_AFTER_NOT_CONNECTED_SECONDS = 120
FULL_PUBLISH_MIN_INTERVAL_SECONDS = 45
MINIMUM_FULLY_SUPPORTED_VERSION = 3.5

# Modify the logger to include instance_id without changing the tracing level
# class InstanceIDFilter(logging.Filter):
#     def __init__(self, instance_id):
#         super().__init__()
#         self.instance_id = instance_id

#     def filter(self, record):
#         record.instance_id = self.instance_id
#         return True

# Update the log format to include instance_id with a default value if not present
# for handler in logging.getLogger().handlers:
#     handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - [ID: %(instance_id)s] - %(message)s', defaults={'instance_id': 'N/A'}))

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

CallbackOnNewMetric = Callable[["Hub", Device, Metric], None]

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
        topic_log_info: str | None = None,
        operation_mode: OperationMode = OperationMode.FULL,
        device_type_exclude_filter: list[DeviceType] | None = None,
        update_frequency_seconds: int | None = None,
    ) -> None:
        """
        Initialize a Hub instance for communicating with a Venus OS MQTT broker.

        Parameters
        ----------
        host: str
            MQTT broker hostname or IP address.
        port: int
            MQTT broker port (1-65535).
        username: str | None
            Username for MQTT authentication, or None for anonymous access.
        password: str | None
            Password for MQTT authentication, or None.
        use_ssl: bool
            If True, an SSL/TLS context will be configured when connecting.
        installation_id: str | None
            If provided, used to replace `{installation_id}` placeholders in topics.
            If None, the installation id will be discovered from the broker when
            `connect()` is called.
        model_name: str | None
            Optional device model name used for informational purposes.
        serial: str | None
            Optional device serial identifier (defaults to "noserial").
        topic_prefix: str | None
            Optional prefix that is prepended to every subscribe/publish topic.
        topic_log_info: str | None
            Optional substring used to elevate logging level for matching topics.
        operation_mode: OperationMode
            Controls which TopicDescriptor entries are active (e.g. FULL, READ_ONLY,
            EXPERIMENTAL).
        device_type_exclude_filter: list[DeviceType] | None
            Optional list of device types to exclude from subscriptions.
        update_frequency_seconds: int | None
            Optional update frequency used by metrics.
            if None = Update only when source data change
            if 0 = Update as new mqtt data received
            if > 0 = Update at the specified interval (in seconds) even if no new data is received

        Behavior
        --------
        - Performs strict parameter validation and raises `ValueError` or `TypeError`
          for invalid values or types.
        - Builds internal topic maps and subscription lists from the package-level
          `topics` list, applying operation mode and device type filters.
        - Generates a unique MQTT client id and creates (but does not connect)
          a paho-mqtt Client instance. No network operations occur during
          initialization; call `connect()` to establish the MQTT connection.

        Raises
        ------
        ValueError
            If `host` is empty or `port` is out of the valid range.
        TypeError
            If an argument has an incorrect type.
        """
        global running_client_id
        self._instance_id = running_client_id
        running_client_id += 1

        # Add the instance_id filter to the logger only if it doesn't already exist
        # self.logger = logging.getLogger(__name__)
        # self.logger.addFilter(InstanceIDFilter(self._instance_id))
        # if logger_level is not None:
        #     self.logger.setLevel(logger_level)

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
        if topic_log_info is not None and not isinstance(topic_log_info, str):
            raise TypeError(f"topic_log_info must be a string or None, got type={type(topic_log_info).__name__}, value={topic_log_info!r}")
        if not isinstance(operation_mode, OperationMode):
            raise TypeError(f"operation_mode must be an instance of OperationMode, got type={type(operation_mode).__name__}, value={operation_mode!r}")
        if device_type_exclude_filter is not None and not isinstance(device_type_exclude_filter, list):
            raise TypeError(f"device_type_exclude_filter must be a list or None, got type={type(device_type_exclude_filter).__name__}, value={device_type_exclude_filter!r}")
        if device_type_exclude_filter is not None:
            for device_type in device_type_exclude_filter:
                if not isinstance(device_type, DeviceType):
                    raise TypeError(f"device_type_filter must contain only DeviceType instances, got type={type(device_type).__name__}, value={device_type!r}")
        if update_frequency_seconds is not None and not isinstance(update_frequency_seconds, int):
            raise TypeError(f"update_frequency_seconds must be an integer or None, got type={type(update_frequency_seconds).__name__}, value={update_frequency_seconds!r}")
        _LOGGER.info(
            "Initializing Hub[ID: %d](host=%s, port=%d, username=%s, use_ssl=%s, installation_id=%s, model_name=%s, topic_prefix=%s, operation_mode=%s, device_type_exclude_filter=%s, update_frequency_seconds=%s, topic_log_info=%s)",
            self._instance_id, host, port, username, use_ssl, installation_id, model_name, topic_prefix, operation_mode, device_type_exclude_filter, update_frequency_seconds, topic_log_info,
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
        self._keepalive_task = None
        self._connected_event = asyncio.Event()
        self._on_new_metric: CallbackOnNewMetric | None = None
        self._topic_log_info = topic_log_info
        self._operation_mode = operation_mode
        self._device_type_exclude_filter = device_type_exclude_filter
        self._update_frequency_seconds = update_frequency_seconds
        # The client ID is generated using a random string and the instance ID. It has to be unique between all clients connected to the same mqtt server. If not, they may reset each other connection.
        random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        self._client_id = f"victron_mqtt-{random_string}-{self._instance_id}"
        self._keepalive_counter = 0
        self._metrics_placeholders: dict[str, MetricPlaceholder] = {}
        self._fallback_placeholders: dict[str, FallbackPlaceholder] = {}
        self._all_metrics: dict[str, Metric] = {}
        self._first_connect = True
        self._first_full_publish = True
        self._connect_failed_attempts = 0
        self._connect_failed_reason: Exception | None = None
        # Track when _handle_full_publish_message was last invoked for our client
        # Use monotonic time to avoid issues with system clock changes
        self._last_full_publish_called: float = 0.0
        self._firmware_version: float = 0.0
        self._connect_failed_since: float = 0.0

        # Filter the active topics
        metrics_active_topics: list[TopicDescriptor] = []
        self._service_active_topics: dict[str, TopicDescriptor] = {}
        for topic in topics:
            if operation_mode != OperationMode.EXPERIMENTAL and topic.experimental:
                continue
            if topic.message_type == MetricKind.SERVICE:
                self._service_active_topics[topic.short_id] = topic
            else:
                #if operation_mode is READ_ONLY we should change all TopicDescriptor to SENSOR and BINARY_SENSOR
                if operation_mode != OperationMode.READ_ONLY or topic.message_type in [MetricKind.ATTRIBUTE, MetricKind.SENSOR, MetricKind.BINARY_SENSOR]:
                    metrics_active_topics.append(topic)
                else: # READ ONLY and writable topic
                    #deep copy the topic
                    new_topic = copy.deepcopy(topic)
                    new_topic.message_type = MetricKind.BINARY_SENSOR if topic.message_type == MetricKind.SWITCH else MetricKind.SENSOR
                    metrics_active_topics.append(new_topic)

        # Replace all {placeholder} patterns with + for MQTT wildcards
        expanded_topics = Hub.expand_topic_list(metrics_active_topics)
        # Apply device type filtering if specified
        if self._device_type_exclude_filter is not None and len(self._device_type_exclude_filter) > 0:
            relevant_topics = []
            for td in expanded_topics:
                if td.message_type == MetricKind.ATTRIBUTE:
                    relevant_topics.append(td)
                    continue
                topic_device_types = topic_to_device_type(td.topic.split("/"))
                assert topic_device_types is not None
                if topic_device_types in self._device_type_exclude_filter:
                    _LOGGER.info("Topic %s is filtered by device type: %s", td.topic, topic_device_types)
                else:
                    relevant_topics.append(td)
            expanded_topics = relevant_topics

        def merge_is_adjustable_suffix(desc: TopicDescriptor) -> str:
            """Merge the topic with its adjustable suffix."""
            assert desc.is_adjustable_suffix is not None
            return desc.topic.rsplit('/', 1)[0] + '/' + desc.is_adjustable_suffix

        # Helper to build a map where duplicate keys accumulate values in a list
        def build_multi_map(items, key_func):
            result = {}
            for item in items:
                # No need to index formula topics, they are discovered by _pending_formula_topics
                if item.is_formula:
                    continue
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
        subscription_list1 = [Hub._remove_placeholders(topic.topic) for topic in expanded_topics if not topic.is_formula]
        subscription_list2 = [Hub._remove_placeholders(merge_is_adjustable_suffix(topic)) for topic in expanded_topics if topic.is_adjustable_suffix and not topic.is_formula]
        self._subscription_list = subscription_list1 + subscription_list2
        self._pending_formula_topics: list[TopicDescriptor] = [topic for topic in expanded_topics if topic.is_formula]
        for topic in self._pending_formula_topics:
            _LOGGER.info("Formula topic detected: %s", topic.topic)
        self._client = MQTTClient(callback_api_version=CallbackAPIVersion.VERSION2, client_id=self._client_id)
        _LOGGER.info("Hub initialized. Client ID: %s", self._client_id)

    async def connect(self) -> None:
        """Connect to the hub."""
        _LOGGER.info("Connecting to MQTT broker at %s:%d", self.host, self.port)
        assert self._client is not None

        # Based on https://community.victronenergy.com/t/cerbo-mqtt-webui-network-security-profile-configuration/34112
        # it seems that Cerbos will not allow you to configure username, only passwords.
        # still, you do need to put in some username to get the MQTT client work.
        if self.password is not None:
            username = "victron_mqtt" if self.username is None else self.username
            _LOGGER.info("Setting auth credentials for user: %s", self.username)
            self._client.username_pw_set(username, self.password)
        
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
        self._connect_failed_attempts = 0
        self._connect_failed_since = 0.0
        self._connect_failed_reason = None
        self._loop = asyncio.get_event_loop()
        #self._loop.set_task_factory(lambda loop, coro: TracedTask(coro, loop=loop, name=name))
        self._last_full_publish_called = time.monotonic() # Initialize last full publish time


        _LOGGER.info("Starting paho mqtt")
        self._client.loop_start()
        _LOGGER.info("Connecting")
        self._client.connect_async(self.host, self.port)
        _LOGGER.info("Waiting for connection event")
        await self._wait_for_connect()
        if self._client is None:
            raise CannotConnectError("Got request to disconnect while still connecting")
        if self._connect_failed_reason is not None:
            reraise_same_exception(self._connect_failed_reason)
        _LOGGER.info("Successfully connected to MQTT broker at %s:%d", self.host, self.port)
        if self._installation_id is None:
            _LOGGER.info("No installation ID provided, attempting to read from device")
            self._installation_id = await self._read_installation_id()
        # First we need to replace the installation ID in the subscription topics
        new_list: list[str] = []
        for topic in self._subscription_list:
            new_topic = topic.replace("{installation_id}", self._installation_id)
            new_list.append(new_topic)
        self._subscription_list = new_list
        # First setup subscriptions will happen here as we need the installation ID.
        # Later we will do it from the connect callback
        self._setup_subscriptions()
        self._start_keep_alive_loop()
        _LOGGER.info("Connected. Installation ID: %s", self._installation_id)

    def publish(self, topic_short_id: str, device_id: str, value: str | float | int | None) -> None:
        """Publish a message to the MQTT broker."""
        _LOGGER.info("Publishing message to topic_short_id: %s, device_id: %s, value: %s", topic_short_id, device_id, value)
        topic_desc = self._service_active_topics.get(topic_short_id)
        if topic_desc is None:
            _LOGGER.error("No active topic found for topic_short_id: %s", topic_short_id)
            raise TopicNotFoundError(f"No active topic found for topic_short_id: {topic_short_id}")
        assert self._installation_id is not None, "Installation ID must be set before publishing"
        assert device_id is not None, "Device ID must be provided"
        topic = topic_desc.topic.replace("{installation_id}", self._installation_id).replace("{device_id}", device_id)
        payload = WritableMetric._wrap_payload(topic_desc, value) if value is not None else ""
        self._publish(topic, payload)

    def _on_log(self, client: MQTTClient, userdata: Any, level:int, buf:str) -> None:
        _LOGGER.log(level, buf)

    def _on_connect(self, client: MQTTClient, userdata: Any, flags: ConnectFlags, reason_code: ReasonCode, properties: Optional[Properties] = None) -> None:
        try:
            self._on_connect_internal(client, userdata, flags, reason_code, properties)
        except Exception as exc:
            _LOGGER.exception("_on_connect exception %s: %s", type(exc), exc, exc_info=True)
            self._connect_failed_reason = exc
        
        try:
            if self._loop.is_running():
                self._loop.call_soon_threadsafe(self._connected_event.set)
        except Exception as exc:
            _LOGGER.exception("Exception in _on_connect while setting connected event: %s", exc)

    def _on_connect_internal(self, client: MQTTClient, userdata: Any, flags: ConnectFlags, reason_code: ReasonCode, properties: Optional[Properties] = None) -> None:
        """Handle connection callback."""
        self._connect_failed_since = 0
        if self._client is None:
            _LOGGER.warning("Got new connection while self._client is None, ignoring")
            return
        if reason_code.is_failure:
            # Check if this is an authentication failure (value 134 for MQTT v5 or 4/5 for MQTT v3.1.1)
            # ReasonCode value 134 = "Bad user name or password" in MQTT v5
            # ReasonCode value 135 = "Not authorized" in MQTT v5
            # ConnackCode 4 = CONNACK_REFUSED_BAD_USERNAME_PASSWORD in MQTT v3.1.1  
            # ConnackCode 5 = CONNACK_REFUSED_NOT_AUTHORIZED in MQTT v3.1.1
            # I am not sure that v3.1.1 will ever be used here, but just in case.
            _LOGGER.warning("Failed to connect with error code: %s. flags: %s", reason_code, flags)
            if reason_code.value in (134, 135, 4, 5):
                raise AuthenticationError(f"Authentication failed: {connack_string(reason_code)}")
            else:
                raise CannotConnectError(f"Failed to connect to MQTT broker: {self.host}:{self.port}. Error: {connack_string(reason_code)}")
            
        _LOGGER.info("Connected to MQTT broker successfully")
        self._setup_subscriptions()

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
        payload = message.payload.decode()

        # Determine log level based on the substring
        is_info_level = self._topic_log_info and self._topic_log_info in topic
        log_debug = _LOGGER.info if is_info_level else _LOGGER.debug

        log_debug("Message received: topic=%s, payload=%s", topic, payload)

        # Remove topic prefix before processing
        topic = self._remove_topic_prefix(topic)

        if "full_publish_completed" in topic:
            self._handle_full_publish_message(payload)
            return

        if self._installation_id is None and not self._installation_id_event.is_set():
            self._handle_installation_id_message(topic)

        self._handle_normal_message(topic, payload, log_debug)

        # Ensure _handle_full_publish_message runs at least once every interval.
        # This is to handle old cerbo versions that do not send full publish completed messages.
        # Issue #139 and #205
        now = time.monotonic()
        # If we've never called it or it's been longer than the configured interval,
        # call _handle_full_publish_message with an empty payload to trigger periodic handling.
        if now - self._last_full_publish_called >= FULL_PUBLISH_MIN_INTERVAL_SECONDS:
            _LOGGER.debug("Periodic trigger: calling _handle_full_publish_message (last %.1fs ago)", now - self._last_full_publish_called)
            # Use an empty JSON object.
            self._handle_full_publish_message("{}")

    def is_formula_dependency_met(self, topic: TopicDescriptor, relevant_device: Device, key_values: dict[str, str]) -> Tuple[bool, list[Metric]]:
        if not topic.depends_on:
            return True, []
        dependencies: list[Metric] = []
        for dependency in topic.depends_on:
            metric_unique_id = ParsedTopic.make_unique_id(relevant_device.unique_id, dependency)
            metric_unique_id = ParsedTopic.replace_ids(metric_unique_id, key_values)
            dependency_metric = self._all_metrics.get(metric_unique_id)
            if dependency_metric is None:
                _LOGGER.debug("Formula topic %s is missing dependency metric: %s", topic.topic, metric_unique_id)
                return False, []
            dependencies.append(dependency_metric)
        return True, dependencies

    def is_regular_dependency_met(self, metric_placeholder: MetricPlaceholder) -> bool:
        if not metric_placeholder.topic_descriptor.depends_on:
            return True
        for dependency in metric_placeholder.topic_descriptor.depends_on:
            metric_id = ParsedTopic.replace_ids(dependency, metric_placeholder.parsed_topic.key_values)
            dependency_metric = self._all_metrics.get(metric_id)
            dependency_placeholder = self._metrics_placeholders.get(metric_id)
            if dependency_metric is None and dependency_placeholder is None:
                _LOGGER.debug("Regular topic %s is missing dependency metric: %s", metric_placeholder.parsed_topic.full_topic, metric_id)
                return False
        return True

    def _handle_full_publish_message(self, payload: str) -> None:
        """Handle full publish message."""
        echo = self.get_keepalive_echo(payload)
        if not echo:
            if self._first_full_publish:
                _LOGGER.error("No echo found in keepalive message: %s. Probably old Venus OS version", payload)
            else:
                _LOGGER.debug("No echo found in keepalive message: %s. Probably old Venus OS version", payload)

        # Check if it matches our client ID so we got full cycle or refresh
        if echo and not echo.startswith(self._client_id):
            _LOGGER.debug("Not our echo: %s", echo)
            return
        # Update the last-called timestamp when we handled a full-publish for our client
        self._last_full_publish_called = time.monotonic()
        
        _LOGGER.debug("Full publish completed: %s", echo)
        new_metrics: list[tuple[Device, Metric]] = []
        if len(self._metrics_placeholders) > 0:
            fallback_placeholders_list = list(self._fallback_placeholders.values())
            for metric_placeholder in self._metrics_placeholders.values():
                # Check if depedency met, if not, the topic will get ignored
                if not self.is_regular_dependency_met(metric_placeholder):
                    continue
                metric = metric_placeholder.device._create_metric_from_placeholder(metric_placeholder, fallback_placeholders_list, self)
                self._all_metrics[metric.unique_id] = metric
                new_metrics.append((metric_placeholder.device, metric))
        self._metrics_placeholders.clear()
        self._fallback_placeholders.clear()
        # Activate formula entities
        if len(new_metrics) > 0:
            for topic in self._pending_formula_topics:
                _LOGGER.debug("Trying to resolve formula topic: %s", topic)
                relevant_devices: list[Device] = [device for device in self._devices.values() if device.device_type.code == topic.topic.split("/")[1]]
                for device in relevant_devices:
                    # We need all depends_on metric to get the key_values associated with it to be able to generate new metrics per moniker.
                    all_new_metrics_with_same_depends_on_generic_id = [t[1] for t in new_metrics if t[1]._device == device and t[1].generic_short_id == topic.depends_on[0]]
                    for depends_on_metric in all_new_metrics_with_same_depends_on_generic_id:
                        metric_unique_id = ParsedTopic.make_unique_id(device.unique_id, topic.short_id)
                        metric_unique_id = ParsedTopic.replace_ids(metric_unique_id, depends_on_metric.key_values)
                        if self._all_metrics.get(metric_unique_id) is not None:
                            continue
                        is_met, dependencies = self.is_formula_dependency_met(topic, device, depends_on_metric.key_values)
                        if not is_met:
                            continue
                        _LOGGER.info("Formula topic resolved: %s", topic)
                        metric = device._add_formula_metric(topic, self, depends_on_metric.key_values)
                        depends_on: dict[str, Metric] = {}
                        for dependency_metric in dependencies:
                            dependency_metric.add_dependency(metric)
                            depends_on[dependency_metric.unique_id] = dependency_metric
                        metric.init(depends_on, _LOGGER.debug)
                        _LOGGER.info("Formula metric created: %s", metric)
                        self._all_metrics[metric.unique_id] = metric
                        new_metrics.append((device, metric))
        # We are sending the new metrics now as we can be sure that the metric handled all the attribute topics and now ready.
        for device, metric in new_metrics:
            metric.phase2_init(device.unique_id, self._all_metrics)
            try:
                if callable(self._on_new_metric):
                    if self._loop.is_running():
                        # If the event loop is running, schedule the callback
                        self._loop.call_soon_threadsafe(self._on_new_metric, self, device, metric)
            except Exception as exc:
                _LOGGER.error("Error calling _on_new_metric callback %s", exc, exc_info=True)
        # Trace the version once
        if self._first_full_publish:
            version_metric_name = "system_0_platform_venus_firmware_installed_version"
            version_metric = self._all_metrics.get(version_metric_name)
            if version_metric and version_metric.value:
                if version_metric.value[0] == "v":
                    try:
                        # Accept versions like 'v3.70' and 'v3.70~15' by stripping any '~' suffix
                        ver_str = version_metric.value[1:]
                        if "~" in ver_str:
                            ver_str = ver_str.split("~", 1)[0]
                        self._firmware_version = float(ver_str)
                        if self._firmware_version < MINIMUM_FULLY_SUPPORTED_VERSION:
                            _LOGGER.warning("Firmware version is below v3.5: %s. Reduced functionality may occur.", version_metric.value)
                        else:
                            _LOGGER.info("Firmware version is good enough: %s", version_metric.value)
                    except (ValueError, TypeError):
                        _LOGGER.error("Firmware version format not float: %s", version_metric.value)
                else:
                    _LOGGER.error("Firmware version format not supported: %s", version_metric.value)
            else:
                _LOGGER.warning("Version metric not found: %s", version_metric_name)
        if self._loop.is_running():
            self._loop.call_soon_threadsafe(self._first_refresh_event.set)
        self._first_full_publish = False
        _LOGGER.debug("Full publish handling completed")
        
    def _handle_installation_id_message(self, topic: str) -> None:
        """Handle installation ID message."""
        parsed_topic = ParsedTopic.from_topic(topic)
        if parsed_topic is None:
            _LOGGER.info("Ignoring installation ID handling - could not parse topic: %s", topic)
            return

        self._installation_id = parsed_topic.installation_id
        _LOGGER.info("Installation ID received: %s. Original topic: %s", self._installation_id, topic)
        if self._loop.is_running():
            self._loop.call_soon_threadsafe(self._installation_id_event.set)

    def _handle_normal_message(self, topic: str, payload: str, log_debug) -> None:
        """Handle regular MQTT message."""
        parsed_topic = ParsedTopic.from_topic(topic)
        if parsed_topic is None:
            log_debug("Ignoring message - could not parse topic: %s", topic)
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
            log_debug("Ignoring message - no descriptor found for topic: %s", topic)
            return
        if len(desc_list) == 1:
            desc = desc_list[0]
        else:
            desc = parsed_topic.match_from_list(desc_list)
            if desc is None:
                log_debug("Ignoring message - no matching descriptor found for list of topic: %s", topic)
                return

        device = self._get_or_create_device(parsed_topic, desc)
        placeholder = device.handle_message(fallback_to_metric_topic, topic, parsed_topic, desc, payload, self._loop, log_debug, self)
        if isinstance(placeholder, MetricPlaceholder):
            existing_placeholder = self._metrics_placeholders.get(placeholder.parsed_topic.unique_id)
            if existing_placeholder:
                log_debug("Replacing existing metric placeholder: %s", existing_placeholder)
            self._metrics_placeholders[placeholder.parsed_topic.unique_id] = placeholder
        elif isinstance(placeholder, FallbackPlaceholder):
            existing_placeholder = self._fallback_placeholders.get(placeholder.parsed_topic.unique_id)
            if existing_placeholder:
                log_debug("Replacing existing fallback placeholder: %s", existing_placeholder)
            self._fallback_placeholders[placeholder.parsed_topic.unique_id] = placeholder

    async def disconnect(self) -> None:
        """Disconnect from the hub."""
        _LOGGER.info("Disconnecting from MQTT broker")
        self._stop_keepalive_loop()
        await asyncio.sleep(0.1)
        if self._client is None:
            _LOGGER.debug("No client to disconnect")
            return
        if self._client.is_connected():
            self._client.disconnect()
            _LOGGER.info("Disconnected from MQTT broker")
            # Give a small delay to allow any pending MQTT messages to be processed
            await asyncio.sleep(0.1)
        self._client = None

    async def _keepalive(self) -> None:
        """Send a keep alive message to the hub. Updates will only be made to the metrics
        for the 60 seconds following this method call."""
        # Docuementation: https://github.com/victronenergy/dbus-flashmq
        keep_alive_topic = f"R/{self._installation_id}/keepalive"

        if self._client is None:
            _LOGGER.warning("Cannot send keepalive - no MQTT client")
            return
        if not self._client.is_connected():
            _LOGGER.warning("Cannot send keepalive - client is not connected")
            return
        _LOGGER.debug("Sending keepalive message to topic: %s", keep_alive_topic)
        self._keepalive_counter += 1
        keepalive_value = Hub.generate_keepalive_options(f"{self._client_id}-{self._keepalive_counter}")
        self._publish(keep_alive_topic, keepalive_value)

    def _publish(self, topic: str, value: PayloadType) -> None:
        assert self._client is not None
        # Determine log level based on the substring
        is_info_level = self._topic_log_info and self._topic_log_info in topic
        log_debug = _LOGGER.info if is_info_level else _LOGGER.debug

        prefixed_topic = self._add_topic_prefix(topic)
        log_debug("Publishing message to topic: %s, value: %s", prefixed_topic, value)
        self._client.publish(prefixed_topic, value)

    async def _keepalive_loop(self) -> None:
        """Run keepalive every 30 seconds."""
        _LOGGER.info("Starting keepalive loop")
        count = 0
        while True:
            try:
                await self._keepalive()
                await asyncio.sleep(30)
                # We should keep alive all metrics every 60 seconds
                count += 1
                # Old firmwars dont resend values after the keepalive message so we cant use this logic of invalidation if there is no new value
                if self._firmware_version >= MINIMUM_FULLY_SUPPORTED_VERSION and count % 2 == 0:
                    self._keepalive_metrics()
            except asyncio.CancelledError:
                _LOGGER.info("Keepalive loop canceled")
                raise
            except Exception as exc:
                _LOGGER.error("Error in keepalive loop: %s", exc, exc_info=True)
                await asyncio.sleep(5)  # Short delay before retrying

    def _keepalive_metrics(self, force_invalidate: bool = False) -> None:
        """Keep alive all metrics."""
        _LOGGER.debug("Keeping alive all metrics")
        for metric in self._all_metrics.values():
            # Determine log level based on the substring
            is_info_level = self._topic_log_info and self._topic_log_info in metric._descriptor.topic
            log_debug = _LOGGER.info if is_info_level else _LOGGER.debug

            metric._keepalive(force_invalidate, log_debug)

    def _start_keep_alive_loop(self) -> None:
        """Start the keep_alive loop."""
        _LOGGER.info("Creating keepalive task")
        if self._keepalive_task is None or self._keepalive_task.done():
            self._keepalive_task = asyncio.create_task(self._keepalive_loop())
        else:
            _LOGGER.warning("Keepalive task already running")

    def _stop_keepalive_loop(self) -> None:
        """Stop the keepalive loop."""
        if self._keepalive_task is not None:
            _LOGGER.info("Cancelling keepalive task")
            self._keepalive_task.cancel()
            self._keepalive_task = None


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
        await self._keepalive()
        await self.wait_for_first_refresh()
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
                    self._unsubscribe("#")
                if self._loop.is_running():
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
                    if self._loop.is_running():
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
        return re.sub(r'\{(?!installation_id\})[^}]+\}', '+', topic)

    @staticmethod
    def _remove_placeholders_map(topic: str) -> str:
        topic_parts = topic.split("/")
        for i, part in enumerate(topic_parts):
            if i == 1:
                topic_parts[i] = "##installation_id##"
            elif i == 2 and part.startswith("{") and part.endswith("}"):
                topic_parts[i] = "##device_type##"
            elif i == 3:
                topic_parts[i] = "##device_id##"
            elif part == "{phase}":
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
        try:
            self._client.subscribe(prefixed_topic)
        except Exception as e:
            _LOGGER.error("Failed to subscribe to %s: %s", prefixed_topic, e)
            raise

    def _unsubscribe(self, topic: str) -> None:
        """Unsubscribe from a topic with automatic prefix handling."""
        assert self._client is not None
        prefixed_topic = self._add_topic_prefix(topic)
        self._client.unsubscribe(prefixed_topic)
        _LOGGER.debug("Unsubscribed from: %s", prefixed_topic)

    def _setup_subscriptions(self) -> None:
        """Subscribe to list of topics."""
        if self._first_connect:
            self._first_connect = False
            _LOGGER.info("Installation ID is not set, skipping subscription setup")
            return
        _LOGGER.info("Setting up MQTT subscriptions")
        assert self._client is not None
        if not self._client.is_connected():
            raise NotConnectedError
        #topic_list = [(topic, 0) for topic in topic_map]
        for topic in self._subscription_list:
            self._subscribe(topic)
        assert self.installation_id is not None
        self._subscribe(f"N/{self.installation_id}/full_publish_completed")
        _LOGGER.info("Subscribed to full_publish_completed notification")

    async def _wait_for_connect(self) -> None:
        """Wait for the first connection to complete."""
        try:
            await asyncio.wait_for(self._connected_event.wait(), timeout=25) # 25 seconds
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout waiting for first first connection")
            raise CannotConnectError("Timeout waiting for first connection")

    async def wait_for_first_refresh(self) -> None:
        """Wait for the first full refresh to complete."""
        _LOGGER.info("Waiting for first refresh")
        try:
            await asyncio.wait_for(self._first_refresh_event.wait(), timeout=60)
            _LOGGER.info("Devices and metrics initialized. Found %d devices", len(self._devices))
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout waiting for first full refresh")
            raise CannotConnectError("Timeout waiting for first full refresh")

    def _get_or_create_device(self, parsed_topic: ParsedTopic, desc: TopicDescriptor) -> Device:
        """Get or create a device based on topic."""
        device_unique_id = parsed_topic.get_device_unique_id()
        device = self._devices.get(device_unique_id)
        if device is None:
            _LOGGER.info("Creating new device: unique_id=%s, parsed_topic=%s", device_unique_id, parsed_topic)
            device = Device(
                device_unique_id,
                parsed_topic,
                desc,
            )
            self._devices[device_unique_id] = device
        return device

    def get_metric(self, unique_id: str) -> Metric | None:
        """Get a metric from a unique id."""
        metric = self._all_metrics.get(unique_id)
        return metric

    @property
    def devices(self) -> dict[str, Device]:
        "Return a list of devices attached to the hub. Requires initialize_devices_and_metrics() to be called first."
        # Return only devices with at least a single metric
        return {k: v for k, v in self._devices.items() if v.metrics}

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
        try:
            _LOGGER.warning("Connection to MQTT broker failed")
            if self._connect_failed_since == 0:
                self._connect_failed_since = time.monotonic()
            self._connect_failed_attempts += 1
            # Check if we have reached the maximum number of failed attempts
            if self._connect_failed_attempts >= CONNECT_MAX_FAILED_ATTEMPTS:
                raise CannotConnectError(f"Failed to connect to MQTT broker: {self.host}:{self.port} after {self._connect_failed_attempts} attempts")
            # This code is not really needed in newer firmwares as metrics will get invalidated individually. With older firmwares, we can force invalidation after we are disconnected for enough time
            disconnected_for = time.monotonic() - self._connect_failed_since
            if disconnected_for > FORCE_INVALIDATE_AFTER_NOT_CONNECTED_SECONDS:
                _LOGGER.info("Disconnected for %d seconds. Invalidating all metrics", disconnected_for)
                self._keepalive_metrics(force_invalidate=True)
                self._connect_failed_since = 0  # Reset the timer
        except Exception as exc:
            _LOGGER.exception("on_connect_fail exception %s: %s", type(exc), exc, exc_info=True)
            self._connect_failed_reason = exc
            if self._loop.is_running():
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
                    expanded.append(replace(
                        td,
                        topic=pattern.sub(str(i), td.topic),
                        key_values={key: str(i)}
                    ))
            else:
                # Use replace to trigger __post_init__ even for unchanged items
                expanded.append(replace(td))
        return expanded

    @property
    def on_new_metric(self) -> CallbackOnNewMetric | None:
        """Returns the on_new_metric callback."""
        return self._on_new_metric

    @on_new_metric.setter
    def on_new_metric(self, value: CallbackOnNewMetric | None):
        """Sets the on_new_metric callback."""
        self._on_new_metric = value

    @staticmethod
    def generate_keepalive_options(echo_value: str) -> str:
        """Generate a JSON string for keepalive options with a configurable echo value."""
        options = {
            "keepalive-options": [
                {"full-publish-completed-echo": echo_value}
            ]
        }
        return json.dumps(options)

    @staticmethod
    def get_keepalive_echo(value: str) -> str | None:
        """Extract the keepalive echo value from the published message."""
        try:
            publish_completed_message = json.loads(value)
            echo = publish_completed_message.get("full-publish-completed-echo", None)
            return echo
        except (json.JSONDecodeError, KeyError, ValueError, TypeError):
            _LOGGER.error("Failed to extract keepalive echo: %s", value)
            return None


class CannotConnectError(Exception):
    """Error to indicate we cannot connect."""


class ProgrammingError(Exception):
    """Error to indicate that we are in a state that should never be reached."""


class NotConnectedError(Exception):
    """Error to indicate that we expected to be connected at this stage but is not."""


class TopicNotFoundError(Exception):
    """Error to indicate that we expected to find a topic but it is not present."""


class AuthenticationError(CannotConnectError):
    """Authentication failed."""
