"""Data classes for Victron Venus OS integration."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging

from ._victron_enums import DeviceType
from .constants import MetricKind, MetricNature, MetricType, RangeType, ValueType, VictronEnum

_LOGGER = logging.getLogger(__name__)

@dataclass
class TopicDescriptor:
    """Describes the topic, how to map it and how to parse it."""
    topic: str
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
    min_max_range: RangeType = RangeType.STATIC
    min: int | None = None
    max: int | None = None
    is_adjustable_suffix: str | None = None
    key_values: dict[str, str] = field(default_factory=dict)

    def __repr__(self) -> str:
        """Return a string representation of the topic."""
        return (
            f"TopicDescriptor(topic={self.topic},"
            f"message_type={self.message_type}, "
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
            f"enum={self.enum}, "
            f"is_adjustable_suffix={self.is_adjustable_suffix}, "
            f"key_values={self.key_values})"
        )
    
    def __post_init__(self):
        assert self.message_type == MetricKind.ATTRIBUTE or self.name is not None
        if self.value_type != ValueType.FLOAT:
            self.precision = None


@dataclass
class ParsedTopic:
    """Parsed topic."""

    installation_id: str
    device_id: str
    device_type: DeviceType
    wildcards_with_device_type: str
    wildcards_without_device_type: str
    full_topic: str

    def __repr__(self) -> str:
        """Return a string representation of the parsed topic."""
        return (
            f"ParsedTopic("
            f"installation_id={self.installation_id}, "
            f"device_id={self.device_id}, "
            f"device_type={self.device_type}, "
            f"wildcards_with_device_type={self.wildcards_with_device_type}, "
            f"wildcards_without_device_type={self.wildcards_without_device_type}, "
            f"full_topic={self.full_topic}"
            f")"
        )
    
    def __hash__(self):
        """Make ParsedTopic hashable for use as dictionary keys."""
        return hash((self.full_topic))

    @classmethod
    def normalize_topic(cls, topic: str) -> str:
        """Normalize a topic by replacing numeric parts with a marker."""
        topic_parts = topic.split("/")
        for i, part in enumerate(topic_parts):
            if part.isdigit():
                topic_parts[i] = "##num##"
            if part in ["L1", "L2", "L3"]:
                topic_parts[i] = "##phase##"
        return "/".join(topic_parts)

    @classmethod
    def from_topic(cls, topic: str) -> ParsedTopic | None:
        """Create a ParsedTopic from a topic and payload."""

        # example : N/123456789012/grid/30/Ac/L1/Energy/Forward
        full_topic = topic
        topic_parts = topic.split("/")

        if len(topic_parts) < 4:  # noqa: PLR2004"
            return None

        wildcard_topic_parts = topic_parts.copy()

        installation_id = topic_parts[1]
        wildcard_topic_parts[1] = "+"
        native_device_type = topic_parts[2]
        if native_device_type == "platform":  # platform is not a device type
            native_device_type = "system"
        # for settings like N/ce3f0ae5476a/settings/0/Settings/CGwacs/AcPowerSetPoint
        elif native_device_type == "settings":
            native_device_type = topic_parts[5]

        device_type = DeviceType.from_code(native_device_type, DeviceType.UNKNOWN)
        if device_type == DeviceType.UNKNOWN: # This can happen as we register for the attribute topics
            _LOGGER.debug("Unknown device type: %s, topic: %s", native_device_type, topic)
            # If the device type is unknown, we cannot create a ParsedTopic
            return None
        
        if device_type == DeviceType.CGWACS:
            device_type = DeviceType.SYSTEM

        device_id = topic_parts[3]
        wildcard_topic_parts[3] = "+"

        wildcards_with_device_type = ParsedTopic.normalize_topic("/".join(wildcard_topic_parts))
        wildcard_topic_parts[2] = "+"
        wildcards_without_device_type = ParsedTopic.normalize_topic("/".join(wildcard_topic_parts))

        return cls(
            installation_id,
            device_id,
            device_type,
            wildcards_with_device_type,
            wildcards_without_device_type,
            full_topic,
        )

    def finalize_topic_fields(self, topic_desc: TopicDescriptor) -> None:
        self._key_values = self.get_key_values(topic_desc)
        self._key_values.update(topic_desc.key_values)
        self._short_id = self._replace_ids(topic_desc.short_id)
        assert topic_desc.name is not None
        self._name = self._replace_ids(topic_desc.name)

    def match_from_list(self, topic_desc_list: list[TopicDescriptor]) -> TopicDescriptor |None:
        topic_parts = self.full_topic.split("/")
        topic_parts[1] = "+"
        topic_parts[3] = "+"
        normalized_topic = "/".join(topic_parts)
        for topic_desc in topic_desc_list:
            if topic_desc.topic == normalized_topic:
                return topic_desc
        return None

    @property
    def short_id(self) -> str:
        return self._short_id

    @property
    def name(self) -> str:
        assert self._name is not None
        return self._name

    @property
    def key_values(self) -> dict[str, str]:
        assert self._key_values is not None
        return self._key_values

    def _replace_ids(self, string: str) -> str:
        """Replace placeholders in the string with matched items from self.key_values."""
        import re

        def replace_match(match):
            key = match.group(1)
            if key in self.key_values:
                return self.key_values[key]
            return match.group(0)  # Leave the placeholder unchanged if no match

        # Match {key} in the string
        pattern = re.compile(r"\{([^{}]+)\}")
        return pattern.sub(replace_match, string)

    def get_key_values(self, topic_desc: TopicDescriptor) -> dict[str, str]:
        topic_parts = self.full_topic.split("/")
        topic_descriptor_parts = topic_desc.topic.split("/")
        result_key_values: dict[str, str] = {}
        for i, part in enumerate(topic_descriptor_parts):
            if part.startswith("{") and part.endswith("}"):
                result_key_values[part.strip("{}")] = topic_parts[i]
        #hack for next phase
        if "phase" in result_key_values:
            result_key_values["next_phase"] = ParsedTopic._get_next_Phase(result_key_values["phase"])
        return result_key_values

    @staticmethod
    def _get_next_Phase(phase: str) -> str:
        """Get the next phase in rotation (L1 -> L2 -> L3 -> L1)."""
        if phase == "L1":
            return "L2"
        elif phase == "L2":
            return "L3"
        elif phase == "L3":
            return "L1"
        else:
            raise ValueError(f"Invalid phase: {phase}. Expected L1, L2, or L3.")
