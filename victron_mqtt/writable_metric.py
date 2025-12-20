"""
Support for Victron Venus WritableMetric.
"""

from __future__ import annotations

from enum import Enum
import logging

from .metric import Metric
from ._unwrappers import VALUE_TYPE_WRAPPER, wrap_bitmask, wrap_enum
from .data_classes import ParsedTopic, TopicDescriptor

_LOGGER = logging.getLogger(__name__)


class WritableMetric(Metric):
    """Representation of a Victron Venus sensor."""

    _min_value: int | float | None = None
    _max_value: int | float | None = None

    def __init__(self, *, descriptor: TopicDescriptor | None = None, topic: str | None = None, **kwargs) -> None:
        """Initialize the WritableMetric."""
        assert descriptor is not None
        _LOGGER.debug(
            "Creating new WritableMetric: short_id=%s, type=%s, nature=%s",
            descriptor.short_id, descriptor.metric_type, descriptor.metric_nature
        )
        self._write_topic: str | None = None
        if topic is not None:
            assert topic.startswith("N")
            self._write_topic = "W" + topic[1:]
        super().__init__(descriptor=descriptor, **kwargs)

    def __str__(self) -> str:
        return f"WritableMetric({super().__str__()}, write_topic = {self._write_topic})"

    def __repr__(self) -> str:
        return self.__str__()

    def phase2_init(self, device_id: str, all_metrics: dict[str, Metric]) -> None:
        """Phase 2 initialization of the WritableMetric."""
        super().phase2_init(device_id, all_metrics)
        self._min_value = self._get_min_max_value(self._descriptor.min, device_id, all_metrics)
        self._max_value = self._get_min_max_value(self._descriptor.max, device_id, all_metrics)

    def _get_min_max_value(
        self, 
        range_value: int | float | str | None, 
        device_id: str, 
        all_metrics: dict[str, Metric]
        ) -> int | float | None:
        """Resolve a range value (min/max) that may be static or reference another metric."""
        if range_value is None:
            return None
        
        if not isinstance(range_value, str):
            # Static numeric value
            return range_value
        
        # Dynamic reference to another metric: "metric_id:default_value"
        parts = range_value.split(":")
        assert len(parts) == 2, f"Range reference must be in format 'metric_id:default_value'. Got: '{range_value}'"        
        dependency_id: str = parts[0]
        default_value: int | float = float(parts[1]) if "." in parts[1] else int(parts[1])
        
        metric_unique_id = ParsedTopic.make_unique_id(device_id, dependency_id)
        metric_unique_id = ParsedTopic.replace_ids(metric_unique_id, self.key_values)
        ref_metric = all_metrics.get(metric_unique_id)
        
        if ref_metric is None:
            _LOGGER.debug(
            "Referenced metric '%s' not found for %s, using default value %s",
            metric_unique_id, self._descriptor.short_id, default_value
            )
            return default_value
        
        return ref_metric.value

    @property
    def min_value(self) -> int | float | None:
        return self._min_value

    @property
    def max_value(self) -> int | float | None:
        return self._max_value

    @property
    def step(self) -> float | int | None:
        return self._descriptor.step

    @property
    def enum_values(self) -> list[str] | None:
        return [e.string for e in self._descriptor.enum] if self._descriptor.enum else None

    def set(self, value: str | float | int | bool | Enum) -> None:
        assert self._write_topic is not None
        payload = WritableMetric._wrap_payload(self._descriptor, value)
        self._hub._publish(self._write_topic, payload)

    @staticmethod
    def _wrap_payload(topic_desc: TopicDescriptor, value: str | float | int | bool | Enum) -> str:
        assert topic_desc.value_type is not None
        wrapper = VALUE_TYPE_WRAPPER[topic_desc.value_type]
        if wrapper in [wrap_enum,wrap_bitmask]:
            return wrapper(value, topic_desc.enum)
        else:
            return wrapper(value)
    
    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value):
        self.set(new_value)
