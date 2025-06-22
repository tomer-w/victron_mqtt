"""
Support for Victron Venus sensors. The sensor itself has no logic,
 it simply receives messages and updates its state.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import logging

from victron_mqtt.constants import PLACEHOLDER_PHASE
from victron_mqtt.data_classes import ParsedTopic, TopicDescriptor

_LOGGER = logging.getLogger(__name__)


class Metric:
    """Representation of a Victron Venus sensor."""

    def __init__(self, unique_id: str, descriptor: TopicDescriptor, parsed_topic: ParsedTopic, value) -> None:
        """Initialize the sensor."""
        _LOGGER.debug(
            "Creating new metric: unique_id=%s, type=%s, nature=%s",
            unique_id, descriptor.metric_type, descriptor.metric_nature
        )
        self._descriptor = descriptor
        self._unique_id = unique_id
        self._value = value
        self._generic_short_id = descriptor.short_id.replace(PLACEHOLDER_PHASE, "lx")
        self._phase = parsed_topic.phase
        self._short_id = descriptor.short_id.replace(PLACEHOLDER_PHASE, parsed_topic.phase) if parsed_topic.phase is not None else None
        self._on_update: Callable | None = None
        _LOGGER.debug("Metric %s initialized with value %s", unique_id, value)

    def __repr__(self) -> str:
        """Return the string representation of the metric."""
        return (
            f"Metric(unique_id={self.unique_id}, "
            f"descriptor={self._descriptor}, "
            f"value={self.value}, "
            f"generic_short_id={self.generic_short_id}, "
            f"phase={self.phase}, "
            f"device_type={self.device_type}, "
            f"short_id={self.short_id})"
            )

    def __str__(self) -> str:
        """Return the string representation of the metric."""
        return self.formatted_value

    @property
    def formatted_value(self) -> str:
        """Returns the formatted value of the metric."""
        if self._value is None:
            return ""

        try:
            fvalue = float(self._value)  # Attempt to convert the object to a float
            if self._descriptor.unit_of_measurement is None:
                return f"{fvalue:.{self._descriptor.precision}f}"
            else:
                return f"{fvalue:.{self._descriptor.precision}f} {self._descriptor.unit_of_measurement}"
        except (ValueError, TypeError):  # Handle cases where conversion fails
            return str(self._value)

    @property
    def value(self):
        """Returns the value of the metric."""
        return self._value

    @property
    def short_id(self) -> str | None:
        """Returns the short id of the metric."""
        return self._short_id

    @property
    def generic_short_id(self) -> str:
        """Returns the generic short id of the metric."""
        return self._generic_short_id

    @property
    def phase(self) -> str:
        """Returns the phase of the metric if referring to a specific AC phase."""
        return self._phase

    @property
    def unit_of_measurement(self) -> str | None:
        """Returns the unit of measurement of the metric."""
        return self._descriptor.unit_of_measurement

    @property
    def metric_type(self):
        """Returns the metric type."""
        return self._descriptor.metric_type

    @property
    def metric_nature(self):
        """Returns the metric nature."""
        return self._descriptor.metric_nature

    @property
    def device_type(self):
        """Returns the device type."""
        return self._descriptor.device_type

    @property
    def precision(self):
        """Returns the precision of the metric."""
        return self._descriptor.precision

    @property
    def unique_id(self) -> str:
        """Return the unique id of the metric."""
        return self._unique_id

    @property
    def on_update(self) -> Callable | None:
        """Returns the on_update callback."""
        return self._on_update

    @on_update.setter
    def on_update(self, value: Callable):
        """Sets the on_update callback."""
        self._on_update = value

    def handle_message(self, parsed_topic, topic_desc, value, event_loop: asyncio.AbstractEventLoop):  # noqa: ARG002 pylint: disable=unused-argument
        """Handle a message."""
        if value != self._value:
            _LOGGER.debug(
                "Metric %s value changed: %s -> %s %s",
                self.unique_id, self._value, value,
                self._descriptor.unit_of_measurement or ''
            )
        self._value = value

        try:
            if callable(self._on_update):
                if event_loop.is_running():
                    # If the event loop is running, schedule the callback
                    _LOGGER.debug("Scheduling on_update callback for metric %s", self.unique_id)
                    event_loop.call_soon_threadsafe(self._on_update, self)
        except Exception as exc:
            _LOGGER.error("Error calling callback %s", exc, exc_info=True)
