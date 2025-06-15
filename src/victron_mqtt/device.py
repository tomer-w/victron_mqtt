"""Logic for handling Victron devices, and routing updates to the appropriate metrics."""

from __future__ import annotations

from logging import getLogger
from typing import TYPE_CHECKING, Optional

from victron_mqtt.constants import DeviceType, PLACEHOLDER_PHASE, MessageType
from victron_mqtt.metric import Metric

if TYPE_CHECKING:
    from victron_mqtt.data_classes import ParsedTopic, TopicDescriptor

_LOGGER = getLogger(__name__)


class Device:
    """Class to represent a Victron device."""

    def __init__(
        self,
        unique_id: str,
        descriptor: TopicDescriptor,
        installation_id: str,
        native_device_type: str,
        device_id: str,
    ) -> None:
        """Initialize."""
        self._descriptor = descriptor
        self._unique_id = unique_id
        self._metrics: dict[str, Metric] = {}
        self._root_device_name: Optional[str] = None
        self._native_device_type = native_device_type
        self._device_type = descriptor.device_type
        self._device_id = device_id
        self._installation_id = installation_id
        self._device_name = ""
        self._model = ""
        self._manufacturer = ""
        self._serial_number = ""
        self._firmware_version = ""

    def __repr__(self) -> str:
        """Return a string representation of the device."""
        return (
            f"Device(unique_id={self.unique_id}, "
            f"name={self.name}, "
            f"model={self.model}, "
            f"manufacturer={self.manufacturer}, "
            f"serial_number={self.serial_number}, "
            f"device_type={self.device_type})"
        )

    def _set_device_property_from_topic(
        self,
        parsed_topic: ParsedTopic,
        topic_desc: TopicDescriptor,
        payload: str,  # noqa: ARG002 pylint: disable=unused-argument
    ) -> None:
        """Set a device property from a topic."""
        short_id = topic_desc.short_id
        if topic_desc.unwrapper is not None:
            payload = str(topic_desc.unwrapper(payload))

        if payload is None:
            return

        if payload == "None":
            return

        if len(payload) == 0:
            return

        if short_id == "victron_productid":
            return  # ignore for now

        if short_id == "model":
            self._model = payload
        elif short_id == "serial_number":
            self._serial_number = payload
        elif short_id == "manufacturer":
            self._manufacturer = payload
        elif short_id == "firmware_version":
            self._firmware_version = payload
        else:
            _LOGGER.warning("Unhandled device property %s for %s", short_id, self.unique_id)

        # if we get a model message and we don't have a name yet, we use the model as name

        if short_id == "model" and self._device_name == "":
            self._device_name = payload

    async def handle_message(self, parsed_topic: ParsedTopic, topic_desc: TopicDescriptor, payload: str) -> None:
        """Handle a message."""

        # if we created the device on a generic topic we need to fix the device type as soon
        #  as we get a more specific topic
        if self.device_type == DeviceType.ANY and topic_desc.device_type != DeviceType.ANY:
            self._device_type = topic_desc.device_type

        if topic_desc.message_type == MessageType.ATTRIBUTE:
            self._set_device_property_from_topic(parsed_topic, topic_desc, payload)
        elif topic_desc.message_type == MessageType.METRIC:
            value = payload
            if topic_desc.unwrapper is not None:
                value = topic_desc.unwrapper(payload)
            if value is None:
                return  # don't try to create or update metric if we don't have valid values for it.

            short_id = topic_desc.short_id
            if PLACEHOLDER_PHASE in short_id:
                short_id = short_id.replace(PLACEHOLDER_PHASE, parsed_topic.phase)
            metric_id = f"{self.unique_id}_{short_id}"

            metric = self._get_or_create_metric(metric_id, short_id, parsed_topic, topic_desc, payload)

            await metric.handle_message(parsed_topic, topic_desc, value)

    def _get_or_create_metric(
        self, metric_id: str, short_id: str, parsed_topic: ParsedTopic, topic_desc: TopicDescriptor, payload: str
    ) -> Metric:
        """Get or create a metric."""
        metric = self._metrics.get(metric_id)
        if metric is None:
            metric = Metric(metric_id, topic_desc, parsed_topic, payload)
            self._metrics[metric_id] = metric
            setattr(self, short_id, metric)

        return metric

    def set_root_device_name(self, name: str) -> None:
        """Set the name of the root device."""
        self._root_device_name = name
        self._device_name = name

    def get_metric_from_unique_id(self, unique_id: str) -> Metric:
        """Get a metric from a unique id."""
        return self._metrics.get(unique_id)

    @property
    def metrics(self) -> list[Metric]:
        """Returns the list of metrics on this device."""
        return list(self._metrics.values())

    @property
    def unique_id(self) -> str:
        """Return the unique id of the device."""
        return self._unique_id

    @property
    def name(self) -> str:
        """Return the name of the device."""
        return self._device_name

    @property
    def model(self) -> str:
        """Return the model of the device."""
        return self._model

    @property
    def manufacturer(self) -> str:
        """Return the manufacturer of the device."""
        return self._manufacturer

    @property
    def serial_number(self) -> str:
        """Return the serial number of the device."""
        return self._serial_number

    @property
    def device_type(self) -> DeviceType:
        """Return the device type."""
        return self._device_type

    @property
    def native_device_type(self) -> str:
        """Return the native device type."""
        return self._native_device_type

    @property
    def firmware_version(self) -> str:
        """Return the firmware version of the device."""
        return self._firmware_version

    @property
    def device_id(self) -> str:
        """Return the device id of the device."""
        return self._device_id
