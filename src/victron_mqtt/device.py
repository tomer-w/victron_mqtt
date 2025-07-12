"""Logic for handling Victron devices, and routing updates to the appropriate metrics."""

from __future__ import annotations

import asyncio
from enum import Enum
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .hub import Hub

from ._unwrappers import VALUE_TYPE_UNWRAPPER, unwrap_enum
from .constants import PLACEHOLDER_PHASE, MetricKind
from .metric import Metric
from ._victron_enums import DeviceType
from .switch import Switch

if TYPE_CHECKING:
    from .data_classes import ParsedTopic, TopicDescriptor

_LOGGER = logging.getLogger(__name__)

class Device:
    """Class to represent a Victron device."""

    def __init__(self, unique_id: str, parsed_topic: ParsedTopic, descriptor: TopicDescriptor) -> None:
        """Initialize."""
        _LOGGER.debug(
            "Creating new device: unique_id=%s, parsed_topic=%s, descriptor=%s",
            unique_id, parsed_topic, descriptor
        )
        self._descriptor = descriptor
        self._unique_id = unique_id
        self._metrics: dict[str, Metric] = {}
        self._device_type = parsed_topic.device_type
        self._native_device_type = parsed_topic.native_device_type
        self._device_id = parsed_topic.device_id
        self._installation_id = parsed_topic.installation_id
        self._device_name = None
        self._model = None
        self._manufacturer = None
        self._serial_number = None
        self._firmware_version = None
        if self._device_type == DeviceType.SYSTEM:
            self._model = self._device_name = "Victron Venus"

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
            f"device_id={self.device_id})"
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
            if self._device_name is None and self._model is not None:
                self._device_name = value
                _LOGGER.debug("Using model as device name: %s", value)
        elif short_id == "serial_number":
            self._serial_number = value
        elif short_id == "manufacturer":
            self._manufacturer = value
        elif short_id == "firmware_version":
            self._firmware_version = value
        else:
            _LOGGER.warning("Unhandled device property %s for %s", short_id, self.unique_id)

    
    def handle_message(self, topic: str, parsed_topic: ParsedTopic, topic_desc: TopicDescriptor, payload: str, event_loop: asyncio.AbstractEventLoop, hub: Hub) -> None:
        """Handle a message."""
        _LOGGER.debug("Handling message for device %s: topic=%s", self.unique_id, parsed_topic)

        if topic_desc.message_type == MetricKind.ATTRIBUTE:
            self._set_device_property_from_topic(parsed_topic, topic_desc, payload)
            return
        
        # It is metric or switch
        value = Device._unwrap_payload(topic_desc, payload)
        if value is None:
            _LOGGER.debug(
                "Ignoring null metric value for device %s metric %s", 
                self.unique_id, topic_desc.short_id
            )
            return

        short_id = topic_desc.short_id
        if PLACEHOLDER_PHASE in short_id:
            assert parsed_topic.phase is not None
            short_id = short_id.replace(PLACEHOLDER_PHASE, parsed_topic.phase)
        metric_id = f"{self.unique_id}_{short_id}"

        metric = self._get_or_create_metric(metric_id, short_id, topic, parsed_topic, topic_desc, payload, hub)
        metric._handle_message(parsed_topic, topic_desc, value, event_loop)

    @staticmethod
    def _unwrap_payload(topic_desc: TopicDescriptor, payload: str) -> str | float | int | type[Enum] | None:
        assert topic_desc.value_type is not None
        unwrapper = VALUE_TYPE_UNWRAPPER[topic_desc.value_type]
        if unwrapper == unwrap_enum:
            return unwrapper(payload, topic_desc.enum)
        else:
            return unwrapper(payload)

    def _get_or_create_metric(
        self, metric_id: str, short_id: str, topic: str, parsed_topic: ParsedTopic, topic_desc: TopicDescriptor, payload: str, hub: Hub
    ) -> Metric:
        """Get or create a metric."""
        metric = self._metrics.get(metric_id)
        if metric is None:
            _LOGGER.info("Creating new metric: metric_id=%s, short_id=%s", metric_id, short_id)
            if topic_desc.message_type in [MetricKind.SWITCH, MetricKind.NUMBER, MetricKind.SELECT]:
                metric = Switch(metric_id, topic_desc, topic, parsed_topic, payload, hub)
            else:
                metric = Metric(metric_id, topic_desc, parsed_topic, payload)
            self._metrics[metric_id] = metric
            setattr(self, short_id, metric)

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
        return self._device_name

    @property
    def model(self) -> str | None:
        """Return the model of the device."""
        return self._model

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
    def native_device_type(self) -> str:
        """Return the device type."""
        return self._native_device_type

    @property
    def firmware_version(self) -> str | None:
        """Return the firmware version of the device."""
        return self._firmware_version

    @property
    def device_id(self) -> str:
        """Return the device id of the device."""
        return self._device_id
