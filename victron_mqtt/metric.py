"""
Support for Victron Venus sensors. The sensor itself has no logic,
 it simply receives messages and updates its state.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import time
import logging
from typing import TYPE_CHECKING, Any

from .id_utils import replace_complex_id_to_simple, replace_complex_ids
from .constants import MetricKind, MetricNature, MetricType
from .data_classes import ParsedTopic, TopicDescriptor

if TYPE_CHECKING:
    from .hub import Hub
    from .device import Device
    from .formula_metric import FormulaMetric

_LOGGER = logging.getLogger(__name__)

CallbackOnUpdate = Callable[["Metric", Any], None]

class Metric:
    """Representation of a Victron Venus sensor."""

    def __init__(self, device: Device, unique_id: str, name: str, descriptor: TopicDescriptor, short_id: str, key_values: dict[str, str], hub: Hub) -> None:
        """Initialize the sensor."""
        _LOGGER.debug(
            "Creating new metric: unique_id=%s, type=%s, nature=%s",
            unique_id, descriptor.metric_type, descriptor.metric_nature
        )
        assert descriptor.name is not None, "name must be set for metric"
        self._device = device
        self._descriptor = descriptor
        self._unique_id = unique_id
        self._value = None
        self._short_id = short_id
        self._name = name
        self._key_values: dict[str, str] = key_values
        self._on_update: CallbackOnUpdate | None = None
        self._generic_name: str | None = None
        self._generic_short_id: str | None = None
        self._depend_on_me: list[FormulaMetric] = []
        self._hub_unique_id: str = f"{device.short_unique_id}_{self._short_id}"
        self._hub = hub
        self._last_update: float = 0
        self._last_seen: float = 0

        _LOGGER.debug("Metric %s initialized", repr(self))

    def __str__(self) -> str:
        """Return the string representation of the metric."""
        key_values_str = ", ".join(f"{k}={v}" for k, v in self._key_values.items())
        key_values_part = f"key_values={{{key_values_str}}}" if key_values_str else "key_values={}"
        return (
            f"Metric(unique_id={self.unique_id}, "
            f"descriptor={self._descriptor}, "
            f"value={self.value}, "
            f"generic_short_id={self._generic_short_id}, "
            f"short_id={self._short_id}, "
            f"generic_name={self._generic_name}, "
            f"name={self._name}, "
            f"{key_values_part})"
            )

    def __repr__(self) -> str:
        return self.__str__()

    def phase2_init(self, device_id: str, all_metrics: dict[str, Metric]) -> None:
        """Second phase of initializing the metric."""
        assert self._descriptor.name is not None, f"name must be set for topic: {self._descriptor.topic}"
        name_temp = ParsedTopic.replace_ids(self._descriptor.name, self._key_values)
        self._name = self._replace_ids(name_temp, device_id, all_metrics)
        self._generic_name = self._descriptor.generic_name
        self._generic_short_id = replace_complex_id_to_simple(self._descriptor.short_id)

    def _replace_ids(self, orig_str: str, device_id: str, all_metrics: dict[str, Metric]) -> str:
        def replace_match(match):
            moniker = match.group('moniker')
            key, suffix = moniker.split(':', 1)
            assert key and suffix, f"Invalid moniker format: {moniker} in topic: {orig_str}"
            metric = all_metrics.get(f"{device_id}_{suffix}")
            if metric:
                result = str(metric.value)
                self.key_values[key] = result
                return result
            return self.key_values[key]

        temp = replace_complex_ids(orig_str, replace_match)
        if temp != orig_str:
            _LOGGER.debug("Replaced complex placeholders in topic: %s", orig_str)
            return temp

        return ParsedTopic.replace_ids(orig_str, self.key_values)

    def add_dependency(self, formula_metric: FormulaMetric) -> None:
        """Add a dependency to the metric."""
        self._depend_on_me.append(formula_metric)

    def format_value(self, value) -> str:
        """Returns the formatted value of the metric."""
        if value is None:
            return ""

        if self._descriptor.unit_of_measurement is None:
            return str(value)
        else:
            return f"{value} {self._descriptor.unit_of_measurement}"

    @property
    def formatted_value(self):
        """Returns the value of the metric."""
        return self.format_value(self._value)

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
        assert self._name is not None, f"Metric name is None for metric: {repr(self)}"
        return self._name
    
    @property
    def generic_name(self) -> str:
        """Returns the generic name of the metric."""
        assert self._generic_name is not None, f"Metric generic_name is None for metric: {repr(self)}"
        return self._generic_name

    @property
    def generic_short_id(self) -> str:
        """Returns the generic short id of the metric."""
        assert self._generic_short_id is not None, f"Metric generic_short_id is None for metric: {repr(self)}"
        return self._generic_short_id

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
    def precision(self) -> int | None:
        """Returns the precision of the metric."""
        return self._descriptor.precision

    @property
    def unique_id(self) -> str:
        """Return the unique id of the metric."""
        return self._unique_id

    @property
    def key_values(self) -> dict[str, str]:
        """Return the key_values dictionary as read-only."""
        return self._key_values

    @property
    def on_update(self) -> CallbackOnUpdate | None:
        """Returns the on_update callback."""
        return self._on_update

    @on_update.setter
    def on_update(self, value: CallbackOnUpdate | None) -> None:
        """Sets the on_update callback."""
        self._on_update = value

    def _keepalive(self, event_loop: asyncio.AbstractEventLoop | None, log_debug: Callable[..., None]):
        """Reset metrics value if no updates or send last values if they got skipped"""
        silence_timeout = min(60, self._hub._update_frequency_seconds * 3) if self._hub._update_frequency_seconds is not None else 60
        now = time.time()
        elapsed = now - self._last_seen
        if elapsed > silence_timeout:
            log_debug("Metric %s has been silent for %.2fs, resetting", self.unique_id, elapsed)
            self._handle_message(None, event_loop, log_debug)
        elif self._last_seen > self._last_update:
            log_debug("Metric %s has been updated at %.2f but not published since %.2fs, re-publishing", self.unique_id, self._last_update, self._last_seen)
            self._handle_message(self._value, event_loop, log_debug)


    def _handle_message(self, value, event_loop: asyncio.AbstractEventLoop | None, log_debug: Callable[..., None]):
        """Handle a message."""
        now = time.time()
        self._last_seen = now

        changed = False
        if value != self._value:
            log_debug(
                "Metric %s value changed: %s -> %s %s",
                self.unique_id, self._value, value,
                self._descriptor.unit_of_measurement or ''
            )
            changed = True
            self._value = value
        else:
            log_debug(
                "Metric %s value unchanged: %s %s",
                self.unique_id, value,
                self._descriptor.unit_of_measurement or ''
            )

        # In case of zero update frequency, always consider changed when MQTT message is received
        if self._hub._update_frequency_seconds == 0:
            changed = True
        # In case of non-zero update frequency, respect the update frequency limit only for numerical values
        elif self._hub._update_frequency_seconds is not None and isinstance(value, (float, int)):
            elapsed = now - self._last_update
            if elapsed < self._hub._update_frequency_seconds:
                _LOGGER.debug(
                    "Update for %s skipped due to frequency limit (%.2fs < %ds)",
                    self.unique_id, elapsed, self._hub._update_frequency_seconds
                )
                changed = False
            else:
                changed = True

        if changed and event_loop and callable(self._on_update) and event_loop.is_running():
            self._last_update = now
            try:
                # If the event loop is running, schedule the callback
                event_loop.call_soon_threadsafe(self._on_update, self, self.value)
            except Exception as exc:
                log_debug("Error calling callback %s", exc, exc_info=True)

        for dependency in self._depend_on_me:
            assert self != dependency, f"Circular dependency detected: {self}"
            dependency._handle_formula(event_loop, log_debug)
