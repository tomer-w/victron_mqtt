"""Data classes for Victron Venus OS integration."""

from __future__ import annotations

from dataclasses import dataclass
import logging

from ._victron_enums import DeviceType
from .constants import MetricKind, MetricNature, MetricType, ValueType, VictronEnum

_LOGGER = logging.getLogger(__name__)

@dataclass
class TopicDescriptor:
    """Describes the topic, how to map it and how to parse it."""

    message_type: MetricKind
    short_id: str  # Unique short id of the attribute/value
    name: str | None  = None # More user friendly name, doesnt have to be unique
    unit_of_measurement: str | None = None
    metric_type: MetricType = MetricType.NONE
    metric_nature: MetricNature = MetricNature.NONE
    device_type: DeviceType = DeviceType.UNKNOWN
    value_type: ValueType | None = None
    precision: int | None = 2
    enum: type[VictronEnum] | None = None
    min: int | None = None
    max: int | None = None

    def __repr__(self) -> str:
        """Return a string representation of the topic."""
        return (
            f"TopicDescriptor(message_type={self.message_type}, "
            f"short_id={self.short_id}, "
            f"name={self.name}, "
            f"unit_of_measurement={self.unit_of_measurement}, "
            f"metric_type={self.metric_type}, "
            f"metric_nature={self.metric_nature}, "
            f"device_type={self.device_type}, "
            f"precision={self.value_type}, "
            f"precision={self.precision}, "
            f"min={self.min}, "
            f"max={self.max}, "
            f"enum={self.enum})"
        )
    
    def __post_init__(self):
        assert self.message_type == MetricKind.ATTRIBUTE or self.name is not None
        if self.value_type in [ValueType.STRING, ValueType.ENUM]:
            self.precision = None

@dataclass
class ParsedTopic:
    """Parsed topic."""

    installation_id: str
    device_id: str
    device_type: DeviceType
    native_device_type: str
    phase: str | None
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
    def __get_index_and_phase(cls, topic_parts: list[str]) -> tuple[int, str | None]:
        """Get the index of the phase and the phase itself."""
        for i, part in enumerate(topic_parts):
            if part in {"L1", "L2", "L3"}:
                return i, part
        return -1, None

    @classmethod
    def from_topic(cls, topic: str) -> ParsedTopic | None:
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
        device_type = DeviceType.from_code(native_device_type, DeviceType.UNKNOWN)
        assert device_type is not None
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
