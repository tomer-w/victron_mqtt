"""Logic for handling Victron devices, and routing updates to the appropriate metrics."""

from __future__ import annotations

import asyncio
from enum import Enum
import logging
from typing import TYPE_CHECKING, Any
import copy

if TYPE_CHECKING:
    from .hub import Hub

from ._unwrappers import VALUE_TYPE_UNWRAPPER, unwrap_bool, unwrap_enum, unwrap_float
from .constants import MetricKind, RangeType
from .metric import Metric
from ._victron_enums import DeviceType
from .switch import Switch
from .data_classes import ParsedTopic, TopicDescriptor

_LOGGER = logging.getLogger(__name__)

class Device:
    """Class to represent a Victron device."""

    def __init__(self, unique_id: str, parsed_topic: ParsedTopic, descriptor: TopicDescriptor) -> None:
        """Initialize."""
        self._descriptor = descriptor
        self._unique_id = unique_id
        self._metrics: dict[str, Metric] = {}
        self._device_type = parsed_topic.device_type
        self._device_id = parsed_topic.device_id
        self._installation_id = parsed_topic.installation_id
        self._model = None
        self._manufacturer = None
        self._serial_number = None
        self._firmware_version = None
        self._custom_name = None
        self._fallback_is_adjustable_first_map: dict[ParsedTopic, bool] = {}
        self._fallback_data_first_map: dict[ParsedTopic, Any] = {} # Any is payload
        self._fallback_handled_set: set[str] = set()

        _LOGGER.debug("Device %s initialized", unique_id)

    def __repr__(self) -> str:
        """Return a string representation of the device."""
        return (
            f"Device(unique_id={self.unique_id}, "
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

    
    def handle_message(self, fallback_to_metric_topic:bool, topic: str, parsed_topic: ParsedTopic, topic_desc: TopicDescriptor, payload: str, event_loop: asyncio.AbstractEventLoop, hub: Hub) -> None:
        """Handle a message."""
        _LOGGER.debug("Handling message for device %s: topic=%s", self.unique_id, parsed_topic)

        if topic_desc.message_type == MetricKind.ATTRIBUTE:
            self._set_device_property_from_topic(parsed_topic, topic_desc, payload)
            return
        
        if fallback_to_metric_topic:
            value = unwrap_bool(payload)
        else:
            value = Device._unwrap_payload(topic_desc, payload)
        if value is None:
            _LOGGER.debug(
                "Ignoring null metric value for device %s metric %s", 
                self.unique_id, topic_desc.short_id
            )
            return

        # It is metric or switch
        is_adjustable = False
        new_topic_desc = topic_desc
        if topic_desc.message_type != MetricKind.SENSOR and topic_desc.is_adjustable_suffix:
            data_topic = topic.rsplit('/', 1)[0] + '/' + topic_desc.topic.rsplit('/', 1)[1] if fallback_to_metric_topic else topic # need to move from the IsAdjustable topic to the original one
            if fallback_to_metric_topic and data_topic in self._fallback_handled_set:
                _LOGGER.debug("Already handled fallback for %s", data_topic)
                return
            if data_topic not in self._fallback_handled_set:
                if fallback_to_metric_topic:
                    assert isinstance(value, bool)
                    data_parsed_topic = ParsedTopic.from_topic(data_topic)
                    assert data_parsed_topic is not None
                    stored_payload = self._fallback_data_first_map.pop(data_parsed_topic, None)
                    if stored_payload is None:
                        _LOGGER.info("Setting fallback for %s to %s", data_parsed_topic, value)
                        self._fallback_is_adjustable_first_map[data_parsed_topic] = value
                        return
                    is_adjustable = value
                    # Setting all the values to restore state
                    payload = stored_payload
                    value = Device._unwrap_payload(topic_desc, payload)
                    parsed_topic = data_parsed_topic
                    topic = data_topic
                    _LOGGER.info("parsed_topic %s is ready. is_adjustable=%s", data_parsed_topic, is_adjustable)
                else:
                    is_adjustable = self._fallback_is_adjustable_first_map.pop(parsed_topic, None)
                    if is_adjustable is None:
                        _LOGGER.info("No is_adjustable for %s yet. Storing topic_desc=%s, value=%s", parsed_topic, topic_desc, value)
                        self._fallback_data_first_map[parsed_topic] = payload
                        return
                    _LOGGER.info("Got both topic and isAdjustable value (%s) for %s", is_adjustable, topic_desc)
                self._fallback_handled_set.add(data_topic)
                if not is_adjustable:
                    new_topic_desc = copy.deepcopy(topic_desc)  # Deep copy
                    new_topic_desc.message_type = MetricKind.SENSOR

        parsed_topic.finalize_topic_fields(topic_desc)
        short_id = parsed_topic.short_id
        metric_id = f"{self.unique_id}_{short_id}"

        metric = self._get_or_create_metric(metric_id, short_id, topic, parsed_topic, new_topic_desc, hub, payload)
        if metric is None:
            _LOGGER.warning("Failed to create metric for %s. payload=%s", topic, payload)
            return
        metric._handle_message(value, event_loop)

    @staticmethod
    def _unwrap_payload(topic_desc: TopicDescriptor, payload: str) -> str | float | int | bool | type[Enum] | None:
        assert topic_desc.value_type is not None
        unwrapper = VALUE_TYPE_UNWRAPPER[topic_desc.value_type]
        if unwrapper == unwrap_enum:
            return unwrapper(payload, topic_desc.enum)
        else:
            return unwrapper(payload)

    def _get_or_create_metric(
        self, metric_id: str, short_id: str, topic: str, parsed_topic: ParsedTopic, topic_desc: TopicDescriptor, hub: Hub, payload: str
    ) -> Metric | None:
        """Get or create a metric."""
        metric = self._metrics.get(metric_id)
        if metric is not None:
            return metric

        _LOGGER.info("Creating new metric: metric_id=%s, short_id=%s", metric_id, short_id)
        new_topic_desc = topic_desc
        if topic_desc.min_max_range == RangeType.DYNAMIC:
            max_value = unwrap_float(payload, "max")
            if max_value is not None:
                _LOGGER.info("Setting dynamic max value to %s for %s", max_value, topic_desc)
                new_topic_desc = copy.deepcopy(new_topic_desc)  # Deep copy
                new_topic_desc.max = int(max_value)
            
            min_value = unwrap_float(payload, "min")
            if min_value is not None:
                _LOGGER.info("Setting dynamic min value to %s for %s", min_value, topic_desc)
                new_topic_desc = copy.deepcopy(new_topic_desc)  # Deep copy
                new_topic_desc.min = int(min_value)

        if topic_desc.message_type in [MetricKind.SWITCH, MetricKind.NUMBER, MetricKind.SELECT]:
            metric = Switch(metric_id, short_id, new_topic_desc, topic, parsed_topic, hub)
        else:
            metric = Metric(metric_id, short_id, new_topic_desc, parsed_topic)
        self._metrics[metric_id] = metric

        return metric

    def get_metric_from_unique_id(self, unique_id: str) -> Metric | Switch | None:
        """Get a metric from a unique id."""
        return self._metrics.get(unique_id)

    @property
    def metrics(self) -> list[Metric | Switch]:
        """Returns the list of metrics on this device."""
        return list(self._metrics.values())

    @property
    def unique_id(self) -> str:
        """Return the unique id of the device."""
        return self._unique_id

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
