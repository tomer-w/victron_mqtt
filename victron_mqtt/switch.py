"""
Support for Victron Venus switches.
"""

from __future__ import annotations

from enum import Enum
import logging

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .hub import Hub
from .metric import Metric
from ._unwrappers import VALUE_TYPE_WRAPPER, wrap_enum
from .data_classes import ParsedTopic, TopicDescriptor

_LOGGER = logging.getLogger(__name__)


class Switch(Metric):
    """Representation of a Victron Venus sensor."""

    def __init__(self, unique_id: str, short_id: str, descriptor: TopicDescriptor, topic: str, parsed_topic: ParsedTopic, hub: Hub) -> None:
        """Initialize the switch."""
        _LOGGER.debug(
            "Creating new switch: unique_id=%s, type=%s, nature=%s",
            unique_id, descriptor.metric_type, descriptor.metric_nature
        )
        self._hub = hub
        assert topic.startswith("N")
        self._write_topic = "W" + topic[1:]
        super().__init__(unique_id, short_id, descriptor, parsed_topic)
    
    def __repr__(self) -> str:
        return f"Switch({super().__repr__()}, write_topic = {self._write_topic})"

    def set(self, value: str | float | int | bool | Enum) -> None:
        payload = Switch._wrap_payload(self._descriptor, value)
        self._hub.publish(self._write_topic, payload)

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
