"""
Support for Victron Venus sensors. The sensor itself has no logic,
 it simply receives messages and updates its state.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import logging

from ._victron_enums import DeviceType
from .constants import MetricKind, MetricNature, MetricType, RangeType
from .data_classes import ParsedTopic, TopicDescriptor

_LOGGER = logging.getLogger(__name__)


class Metric:
    """Representation of a Victron Venus sensor."""

    def __init__(self, unique_id: str, short_id: str, descriptor: TopicDescriptor, parsed_topic: ParsedTopic) -> None:
        """Initialize the sensor."""
        _LOGGER.debug(
            "Creating new metric: unique_id=%s, type=%s, nature=%s",
            unique_id, descriptor.metric_type, descriptor.metric_nature
        )
        assert descriptor.name is not None, "name must be set for metric"
        assert parsed_topic.device_type is not None, "device_type must be set for metric"
        assert parsed_topic.device_type != DeviceType.UNKNOWN, "device_type must not be UNKNOWN for metric"
        
        self._descriptor = descriptor
        self._unique_id = unique_id
        self._value = None
        self._short_id = short_id
        self._name = parsed_topic.name
        self._key_values: dict[str, str] = parsed_topic.key_values
        self._on_update: Callable | None = None
        _LOGGER.debug("Metric %s initialized", repr(self))

    def __repr__(self) -> str:
        """Return the string representation of the metric."""
        key_values_str = ", ".join(f"{k}={v}" for k, v in self._key_values.items())
        key_values_part = f"key_values={{{key_values_str}}}" if key_values_str else "key_values={}"
        return (
            f"Metric(unique_id={self.unique_id}, "
            f"descriptor={self._descriptor}, "
            f"value={self.value}, "
            f"generic_short_id={self.generic_short_id}, "
            f"device_type={self.device_type}, "
            f"short_id={self.short_id}, "
            f"name={self.name}, "
            f"{key_values_part})"
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
    def short_id(self) -> str:
        """Returns the short id of the metric."""
        return self._short_id

    @property
    def name(self) -> str:
        """Returns the short id of the metric."""
        return self._name

    @property
    def generic_short_id(self) -> str:
        """Returns the generic short id of the metric."""
        return self._descriptor.short_id

    @property
    def unit_of_measurement(self) -> str | None:
        """Returns the unit of measurement of the metric."""
        return self._descriptor.unit_of_measurement

    @property
    def metric_type(self) -> MetricType:
        """Returns the metric type."""
        return self._descriptor.metric_type

    @property
    def metric_nature(self) -> MetricNature:
        """Returns the metric nature."""
        return self._descriptor.metric_nature

    @property
    def metric_kind(self) -> MetricKind:
        """Returns the device type."""
        return self._descriptor.message_type

    @property
    def device_type(self) -> DeviceType:
        """Returns the device type."""
        return self._descriptor.device_type

    @property
    def precision(self) -> int | None:
        """Returns the precision of the metric."""
        return self._descriptor.precision

    @property
    def min_value(self) -> int | RangeType | None:
        return self._descriptor.min

    @property
    def max_value(self) -> int | RangeType | None:
        return self._descriptor.max

    @property
    def enum_values(self) -> list[str] | None:
        return [e.string for e in self._descriptor.enum] if self._descriptor.enum else None

    @property
    def unique_id(self) -> str:
        """Return the unique id of the metric."""
        return self._unique_id

    @property
    def key_values(self) -> dict[str, str]:
        """Return the key_values dictionary as read-only."""
        return self._key_values

    @property
    def on_update(self) -> Callable | None:
        """Returns the on_update callback."""
        return self._on_update

    @on_update.setter
    def on_update(self, value: Callable):
        """Sets the on_update callback."""
        self._on_update = value

    def _handle_message(self, value, event_loop: asyncio.AbstractEventLoop):
        """Handle a message."""
        if value != self._value:
            _LOGGER.debug(
                "Metric %s value changed: %s -> %s %s",
                self.unique_id, self._value, value,
                self._descriptor.unit_of_measurement or ''
            )
        else:
            _LOGGER.debug(
                "Metric %s value unchanged: %s %s",
                self.unique_id, value,
                self._descriptor.unit_of_measurement or ''
            )
            return
        
        self._value = value

        try:
            if callable(self._on_update):
                if event_loop.is_running():
                    # If the event loop is running, schedule the callback
                    event_loop.call_soon_threadsafe(self._on_update, self)
        except Exception as exc:
            _LOGGER.error("Error calling callback %s", exc, exc_info=True)
