"""Data classes for Victron Venus OS integration."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import TYPE_CHECKING, Optional

from .constants import DeviceType, MessageType, MetricNature, MetricType

if TYPE_CHECKING:
    from collections.abc import Callable

_LOGGER = logging.getLogger(__name__)

@dataclass
class TopicDescriptor:
    """Describes the topic, how to map it and how to parse it."""

    message_type: MessageType  # 'device', 'sensor', or 'system'
    short_id: str  # short id of the attribute/value (also translation key)
    unit_of_measurement: Optional[str] = None
    metric_type: MetricType = MetricType.NONE
    metric_nature: MetricNature = MetricNature.NONE
    device_type: DeviceType = DeviceType.ANY
    precision: int | None = 2
    unwrapper: Optional[Callable] = None

    def __repr__(self) -> str:
        """Return a string representation of the topic."""
        return (
            f"TopicDescriptor(message_type={self.message_type}, "
            f"short_id={self.short_id}, "
            f"unit_of_measurement={self.unit_of_measurement}, "
            f"metric_type={self.metric_type}, "
            f"metric_nature={self.metric_nature}, "
            f"device_type={self.device_type}, "
            f"precision={self.precision}, "
            f"unwrapper={self.unwrapper})"
        )

@dataclass
class ParsedTopic:
    """Parsed topic."""

    installation_id: str
    device_id: str
    device_type: DeviceType
    native_device_type: str
    phase: str
    wildcards_with_device_type: str
    wildcards_without_device_type: str

    def __repr__(self) -> str:
        """Return a string representation of the parsed topic."""
        return (
            f"ParsedTopic("
            f"installation_id={self.installation_id}, "
            f"device_id={self.device_id}, "
            f"device_type={self.device_type}, "
            f"phase={self.phase}, "
            f"wildcards_with_device_type={self.wildcards_with_device_type}, "
            f"wildcards_without_device_type={self.wildcards_without_device_type}"
            f")"
        )
    
    @classmethod
    def __get_index_and_phase(cls, topic_parts: list[str]) -> tuple[int, str]:
        """Get the index of the phase and the phase itself."""
        for i, part in enumerate(topic_parts):
            if part in {"L1", "L2", "L3"}:
                return i, part
        return -1, ""

    @classmethod
    def from_topic(cls, topic: str) -> Optional[ParsedTopic]:
        """Create a ParsedTopic from a topic and payload."""

        # example : N/123456789012/grid/30/Ac/L1/Energy/Forward
        topic_parts = topic.split("/")

        if len(topic_parts) < 4:  # noqa: PLR2004"
            return None

        wildcard_topic_parts = topic_parts.copy()

        installation_id = topic_parts[1]
        wildcard_topic_parts[1] = "+"
        native_device_type = topic_parts[2]
        if native_device_type == "platform":  # platform is not a device type
            native_device_type = "system"
        try:
            device_type = DeviceType(native_device_type)
        except ValueError as e:
            device_type = DeviceType.ANY
        device_id = topic_parts[3]
        wildcard_topic_parts[3] = "+"

        phase_index, phase = ParsedTopic.__get_index_and_phase(topic_parts)
        if phase_index != -1:
            wildcard_topic_parts[phase_index] = "+"

        wildcards_with_device_type = "/".join(wildcard_topic_parts)

        wildcard_topic_parts[2] = "+"

        wildcards_without_device_type = "/".join(wildcard_topic_parts)

        return cls(
            installation_id,
            device_id,
            device_type,
            native_device_type,
            phase,
            wildcards_with_device_type,
            wildcards_without_device_type,
        )
