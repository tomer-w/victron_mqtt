"""
Support for Victron Venus WritableMetric.
"""

from __future__ import annotations

from enum import Enum
import logging

from typing import TYPE_CHECKING

from victron_mqtt.constants import RangeType
if TYPE_CHECKING:
    from .hub import Hub
from .metric import Metric
from ._unwrappers import VALUE_TYPE_WRAPPER, wrap_enum
from .data_classes import ParsedTopic, TopicDescriptor

_LOGGER = logging.getLogger(__name__)


class WritableMetric(Metric):
    """Representation of a Victron Venus sensor."""

    def __init__(self, unique_id: str, short_id: str, descriptor: TopicDescriptor, topic: str, parsed_topic: ParsedTopic, hub: Hub) -> None:
        """Initialize the WritableMetric."""
        _LOGGER.debug(
            "Creating new WritableMetric: unique_id=%s, type=%s, nature=%s",
            unique_id, descriptor.metric_type, descriptor.metric_nature
        )
        self._hub = hub
        assert topic.startswith("N")
        self._write_topic = "W" + topic[1:]
        super().__init__(unique_id, short_id, descriptor, parsed_topic)
    
    def __repr__(self) -> str:
        return f"WritableMetric({super().__repr__()}, write_topic = {self._write_topic})"

    @property
    def min_value(self) -> int | float | RangeType | None:
        return self._descriptor.min

    @property
    def max_value(self) -> int | float | RangeType | None:
        return self._descriptor.max

    @property
    def step(self) -> float | int | None:
        return self._descriptor.step

    @property
    def enum_values(self) -> list[str] | None:
        return [e.string for e in self._descriptor.enum] if self._descriptor.enum else None

    def set(self, value: str | float | int | bool | Enum) -> None:
        payload = WritableMetric._wrap_payload(self._descriptor, value)
        self._hub._publish(self._write_topic, payload)

    @staticmethod
    def _wrap_payload(topic_desc: TopicDescriptor, value: str | float | int | bool | Enum) -> str:
        assert topic_desc.value_type is not None
        wrapper = VALUE_TYPE_WRAPPER[topic_desc.value_type]
        if wrapper == wrap_enum:
            return wrapper(value, topic_desc.enum)
        else:
            return wrapper(value)
    
    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value):
        self.set(new_value)
