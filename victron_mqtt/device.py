"""Logic for handling Victron devices, and routing updates to the appropriate metrics."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import Enum
import logging
from typing import TYPE_CHECKING, Callable
import copy


if TYPE_CHECKING:
    from .hub import Hub

from ._unwrappers import VALUE_TYPE_UNWRAPPER, unwrap_bool, unwrap_enum, unwrap_float, unwrap_int_seconds_to_hours
from .constants import MetricKind, RangeType
from .metric import Metric
from .formula_metric import FormulaMetric
from ._victron_enums import DeviceType
from .writable_metric import WritableMetric
from .data_classes import ParsedTopic, TopicDescriptor

_LOGGER = logging.getLogger(__name__)

class Device:
    """Class to represent a Victron device."""

    def __init__(self, full_unique_id: str, short_unique_id: str, parsed_topic: ParsedTopic, descriptor: TopicDescriptor) -> None:
        """Initialize."""
        self._descriptor = descriptor
        self._full_unique_id = full_unique_id
        self._short_unique_id = short_unique_id
        self._metrics: dict[str, Metric] = {}
        self._device_type = parsed_topic.device_type
        self._device_id = parsed_topic.device_id
        self._installation_id = parsed_topic.installation_id
        self._model = None
        self._manufacturer = None
        self._serial_number = None
        self._firmware_version = None
        self._custom_name = None

        _LOGGER.debug("Device %s initialized", self._full_unique_id)

    def __repr__(self) -> str:
        """Return a string representation of the device."""
        return (
            f"Device(full_unique_id={self._full_unique_id}, "
            f"short_unique_id={self._short_unique_id}, "
            f"name={self.name}, "
            f"model={self.model}, "
            f"manufacturer={self.manufacturer}, "
            f"serial_number={self.serial_number}, "
            f"device_type={self.device_type}, "
            f"device_id={self.device_id}, "
            f"firmware_version={self.firmware_version}, "
            f"custom_name={self.custom_name})"
        )

    def _set_device_property_from_topic(
        self,
        parsed_topic: ParsedTopic,
        topic_desc: TopicDescriptor,
        payload: str,
    ) -> None:
        """Set a device property from a topic."""
        short_id = topic_desc.short_id
        value = Device._unwrap_payload(topic_desc, payload)

        if value is None:
            _LOGGER.debug("Ignoring empty/None payload for device %s property %s", self.unique_id, short_id)
            return
        value = str(value)

        _LOGGER.debug("Setting device %s property %s = %s", self.unique_id, short_id, value)

        if short_id == "victron_productid":
            return  # ignore for now

        if short_id == "model":
            self._model = value
        elif short_id == "serial_number":
            self._serial_number = value
        elif short_id == "manufacturer":
            self._manufacturer = value
        elif short_id == "firmware_version":
            self._firmware_version = value
        elif short_id == "custom_name":
            self._custom_name = value
        else:
            _LOGGER.warning("Unhandled device property %s for %s", short_id, self.unique_id)


    def handle_message(self, fallback_to_metric_topic: bool, topic: str, parsed_topic: ParsedTopic, topic_desc: TopicDescriptor, payload: str, event_loop: asyncio.AbstractEventLoop, log_debug: Callable[..., None], hub: Hub) -> MetricPlaceholder | FallbackPlaceholder | None:
        """Handle a message."""
        log_debug("Handling message for device %s: topic=%s", self.unique_id, parsed_topic)

        if topic_desc.message_type == MetricKind.ATTRIBUTE:
            self._set_device_property_from_topic(parsed_topic, topic_desc, payload)
            return None

        if fallback_to_metric_topic:
            value = unwrap_bool(payload)
            if value is None:
                log_debug(
                    "Ignoring null fallback_to_metric_topic value for device %s metric %s", 
                    self.unique_id, topic_desc.short_id
                )
                return None
            return FallbackPlaceholder(device=self, metric_id=topic_desc.short_id, parsed_topic=parsed_topic, topic_descriptor=topic_desc, value=value)
        else:
            value = Device._unwrap_payload(topic_desc, payload)
            if value is None:
                log_debug(
                    "Ignoring null fallback_to_metric_topic value for device %s metric %s", 
                    self.unique_id, topic_desc.short_id
                )
                return None

        parsed_topic.finalize_topic_fields(topic_desc)
        short_id = parsed_topic.short_id
        metric_id = f"{self.unique_id}_{short_id}"
        metric = self._metrics.get(metric_id)
        if metric:
            metric._handle_message(value, event_loop, log_debug)
            return None
        assert value is not None, f"Value must not be None. topic={topic}, payload={payload}"
        return MetricPlaceholder(self, metric_id, parsed_topic, topic_desc, payload, value)

    @staticmethod
    def _unwrap_payload(topic_desc: TopicDescriptor, payload: str) -> str | float | int | bool | type[Enum] | None:
        assert topic_desc.value_type is not None
        unwrapper = VALUE_TYPE_UNWRAPPER[topic_desc.value_type]
        if unwrapper == unwrap_enum:
            return unwrapper(payload, topic_desc.enum)
        elif unwrapper in [unwrap_float, unwrap_int_seconds_to_hours]:
            return unwrapper(payload, topic_desc.precision)
        else:
            return unwrapper(payload)

    @staticmethod
    def _is_same_adjustable_topics(topic: str, adjustable_topic: str) -> bool:
        """Check if two topics are the same, considering adjustable suffixes."""
        return topic.rsplit('/', 1)[0] == adjustable_topic.rsplit('/', 1)[0]

    def add_placeholder(self, metric_placeholder: MetricPlaceholder, fallback_placeholders: list[FallbackPlaceholder], hub: Hub) -> Metric:
        _LOGGER.info("Creating new metric on device: %s", metric_placeholder)

        new_topic_desc = metric_placeholder.topic_descriptor

        if new_topic_desc.is_adjustable_suffix:
            # If the topic is adjustable, we need to decide if it should be writable or not.
            # If there is a fallback placeholder for the same adjustable topic, and its value is False,
            # then we switch the topic to read-only (sensor).
            _LOGGER.info("Topic %s is adjustable", new_topic_desc.topic)
            fallback_placeholder = next((fp for fp in fallback_placeholders if Device._is_same_adjustable_topics(fp.parsed_topic.full_topic, metric_placeholder.parsed_topic.full_topic)), None)
            if fallback_placeholder and not fallback_placeholder.value:
                _LOGGER.info("Switching topic from writable to read-only. topic=%s", new_topic_desc.topic)
                new_topic_desc = copy.deepcopy(new_topic_desc)  # Deep copy
                new_topic_desc.message_type = MetricKind.SENSOR
    
        # Handle dynamic min/max range
        if new_topic_desc.min_max_range == RangeType.DYNAMIC:
            max_value = unwrap_float(metric_placeholder.payload, new_topic_desc.precision, "max")
            if max_value is not None:
                _LOGGER.info("Setting dynamic max value to %s for %s", max_value, new_topic_desc)
                new_topic_desc = copy.deepcopy(new_topic_desc)  # Deep copy
                new_topic_desc.max = int(max_value)

            min_value = unwrap_float(metric_placeholder.payload, new_topic_desc.precision, "min")
            if min_value is not None:
                _LOGGER.info("Setting dynamic min value to %s for %s", min_value, new_topic_desc)
                new_topic_desc = copy.deepcopy(new_topic_desc)  # Deep copy
                new_topic_desc.min = int(min_value)

        assert metric_placeholder.topic_descriptor.name is not None
        name = ParsedTopic.replace_ids(metric_placeholder.topic_descriptor.name, metric_placeholder.parsed_topic.key_values)
        assert metric_placeholder.parsed_topic.device_type is not None, "device_type must be set for metric"

        if new_topic_desc.message_type in [MetricKind.SWITCH, MetricKind.NUMBER, MetricKind.SELECT]:
            metric = WritableMetric(self, metric_placeholder.metric_id, name, new_topic_desc, metric_placeholder.parsed_topic, hub)
        else:
            metric = Metric(self, metric_placeholder.metric_id, name, new_topic_desc, metric_placeholder.parsed_topic.short_id, metric_placeholder.parsed_topic.key_values)
        metric._handle_message(metric_placeholder.value, None, _LOGGER.debug)
        self._metrics[metric.unique_id] = metric
        return metric

    def add_formula_metric(self, topic_desc: TopicDescriptor) -> FormulaMetric:
        assert topic_desc.name is not None, "name must be set for topic"
        metric_id = f"{self.unique_id}_{topic_desc.short_id}"
        metric = FormulaMetric(self, metric_id, topic_desc.name, topic_desc)
        self._metrics[metric.unique_id] = metric
        return metric

    def get_metric_from_unique_id(self, unique_id: str) -> Metric | WritableMetric | None:
        """Get a metric from a unique id."""
        return self._metrics.get(unique_id)

    @property
    def metrics(self) -> list[Metric | WritableMetric]:
        """Returns the list of metrics on this device."""
        return list(self._metrics.values())

    @property
    def unique_id(self) -> str:
        """Return the unique id of the device."""
        return self._full_unique_id

    @property
    def short_unique_id(self) -> str:
        """Return the short unique id of the device."""
        return self._short_unique_id

    @property
    def name(self) -> str | None:
        """Return the name of the device."""
        if (custom_name := self.custom_name):
            return custom_name
        if (model := self.model):
            return model
        return self.device_type.string
    
    @property
    def model(self) -> str | None:
        """Return the model of the device."""
        if (model := self._model):
            return model
        
        if self._device_type == DeviceType.SYSTEM:
            return "Victron Venus"

    @property
    def manufacturer(self) -> str | None:
        """Return the manufacturer of the device."""
        return self._manufacturer

    @property
    def serial_number(self) -> str | None:
        """Return the serial number of the device."""
        return self._serial_number

    @property
    def device_type(self) -> DeviceType:
        """Return the device type."""
        return self._device_type

    @property
    def firmware_version(self) -> str | None:
        """Return the firmware version of the device."""
        return self._firmware_version

    @property
    def device_id(self) -> str:
        """Return the device id of the device."""
        return self._device_id

    @property
    def custom_name(self) -> str | None:
        """Return the custom name for devices."""
        return self._custom_name


@dataclass
class MetricPlaceholder:
    device: Device
    metric_id: str
    parsed_topic: ParsedTopic
    topic_descriptor: TopicDescriptor
    payload: str
    value: str | float | int | bool | type[Enum]

    def __repr__(self) -> str:
        return f"MetricPlaceholder(device={self.device}, metric_id={self.metric_id}, parsed_topic={self.parsed_topic}, topic_descriptor={self.topic_descriptor}, payload={self.payload}, value={self.value})"
    
@dataclass
class FallbackPlaceholder:
    device: Device
    metric_id: str
    parsed_topic: ParsedTopic
    topic_descriptor: TopicDescriptor
    value: str | float | int | bool | type[Enum]

    def __repr__(self) -> str:
        return f"FallbackPlaceholder(device={self.device}, metric_id={self.metric_id}, parsed_topic={self.parsed_topic}, topic_descriptor={self.topic_descriptor}, value={self.value})"
