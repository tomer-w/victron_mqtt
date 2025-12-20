"""Data classes for Victron Venus OS integration."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging

from .id_utils import replace_complex_id_to_simple
from ._victron_enums import DeviceType
from .constants import MetricKind, MetricNature, MetricType, RangeType, ValueType, VictronEnum

_LOGGER = logging.getLogger(__name__)


def topic_to_device_type(topic_parts: list[str]) -> DeviceType | None:
    """Extract the device type from the topic."""
    if topic_parts[0] == "$$func":
        result = DeviceType.from_code(topic_parts[1])
        return result
    if len(topic_parts) == 3 and topic_parts[2] == "heartbeat":
        return DeviceType.SYSTEM
    if len(topic_parts) < 2:
        return None
    native_device_type = topic_parts[2]
    # for settings like N/+/settings/0/Settings/CGwacs/AcPowerSetPoint
    if native_device_type == "settings":
        native_device_type = topic_parts[5]
    result = DeviceType.from_code(native_device_type)
    return result


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
    value_type: ValueType | None = None
    precision: int | None = None
    enum: type[VictronEnum] | None = None
    min_max_range: RangeType = RangeType.STATIC
    min: float | int | str | None = None
    max: float | int | str | None = None
    step: float | int | None = None
    is_adjustable_suffix: str | None = None
    key_values: dict[str, str] = field(default_factory=dict)
    experimental: bool = False
    # Depends on format is different for regular and formula topics:
    # For regular topics, the depends_on list contains the {device_id}_{metric_short_id} of the metric it depends on
    # For formula topics, the depends_on list contains the {device_type}_{metric_short_id} of the metrics it depends on as it will be generated for all device ids from the specific device type
    depends_on: list[str] = field(default_factory=list)
    generic_name: str | None = None
    is_formula: bool = False  # True if this topic is calculated from other topics

    def __repr__(self) -> str:
        """Return a string representation of the topic."""
        return (
            f"TopicDescriptor(topic={self.topic},"
            f"message_type={self.message_type}, "
            f"short_id={self.short_id}, "
            f"name={self.name})"
        )
    
    def __post_init__(self):
        assert self.message_type == MetricKind.ATTRIBUTE or self.name is not None
        self.generic_name = replace_complex_id_to_simple(self.name) if self.name else None
        self.is_formula = True if self.topic.startswith("$$func/") else False
        # Voltage default
        if self.metric_type == MetricType.VOLTAGE:
            if self.unit_of_measurement is None:
                self.unit_of_measurement = "V"
            if self.value_type is None:
                self.value_type = ValueType.FLOAT
            if self.precision is None:
                self.precision = 3
            if self.metric_nature == MetricNature.NONE:
                self.metric_nature = MetricNature.INSTANTANEOUS
        # Power default
        if self.metric_type == MetricType.POWER:
            if self.unit_of_measurement is None:
                self.unit_of_measurement = "W"
            if self.value_type is None:
                self.value_type = ValueType.FLOAT
            if self.precision is None:
                self.precision = 1
            if self.metric_nature == MetricNature.NONE:
                self.metric_nature = MetricNature.INSTANTANEOUS
        # Current default
        if self.metric_type == MetricType.CURRENT:
            if self.unit_of_measurement is None:
                self.unit_of_measurement = "A"
            if self.value_type is None:
                self.value_type = ValueType.FLOAT
            if self.precision is None:
                self.precision = 1
            if self.metric_nature == MetricNature.NONE:
                self.metric_nature = MetricNature.INSTANTANEOUS
        # Energy default
        if self.metric_type == MetricType.ENERGY:
            if self.unit_of_measurement is None:
                self.unit_of_measurement = "kWh"
            if self.value_type is None:
                self.value_type = ValueType.FLOAT
            if self.precision is None:
                self.precision = 1
            if self.metric_nature == MetricNature.NONE:
                self.metric_nature = MetricNature.CUMULATIVE
        # frequency default
        if self.metric_type == MetricType.FREQUENCY:
            if self.unit_of_measurement is None:
                self.unit_of_measurement = "Hz"
            if self.value_type is None:
                self.value_type = ValueType.FLOAT
            if self.precision is None:
                self.precision = 2
            if self.metric_nature == MetricNature.NONE:
                self.metric_nature = MetricNature.INSTANTANEOUS
        # Temperature default
        if self.metric_type == MetricType.TEMPERATURE:
            if self.unit_of_measurement is None:
                self.unit_of_measurement = "°C"
            if self.value_type is None:
                self.value_type = ValueType.FLOAT
            if self.precision is None:
                self.precision = 1
            if self.metric_nature == MetricNature.NONE:
                self.metric_nature = MetricNature.INSTANTANEOUS
        # Electric storage capacity default
        if self.metric_type == MetricType.ELECTRIC_STORAGE_CAPACITY:
            if self.unit_of_measurement is None:
                self.unit_of_measurement = "Ah"
            if self.value_type is None:
                self.value_type = ValueType.FLOAT
            if self.precision is None:
                self.precision = 1
            if self.metric_nature == MetricNature.NONE:
                self.metric_nature = MetricNature.INSTANTANEOUS
        # Electric storage percentage default
        if self.metric_type == MetricType.ELECTRIC_STORAGE_PERCENTAGE:
            if self.unit_of_measurement is None:
                self.unit_of_measurement = "%"
            if self.value_type is None:
                self.value_type = ValueType.FLOAT
            if self.precision is None:
                self.precision = 1
            if self.metric_nature == MetricNature.NONE:
                self.metric_nature = MetricNature.INSTANTANEOUS
            if self.min is None:
                self.min = 0
            if self.max is None:
                self.max = 100
        # Apparent power default
        if self.metric_type == MetricType.APPARENT_POWER:
            if self.unit_of_measurement is None:
                self.unit_of_measurement = "VA"
            if self.value_type is None:
                self.value_type = ValueType.FLOAT
            if self.precision is None:
                self.precision = 1
            if self.metric_nature == MetricNature.NONE:
                self.metric_nature = MetricNature.INSTANTANEOUS
        # Time default
        if self.metric_type == MetricType.TIME:
            if self.unit_of_measurement is None:
                self.unit_of_measurement = "s"
            if self.value_type is None:
                self.value_type = ValueType.INT
            if self.metric_nature == MetricNature.NONE:
                self.metric_nature = MetricNature.INSTANTANEOUS
            if self.min is None:
                self.min = 0
            if self.max is None:
                self.max = 86400  # 24 hours in seconds
            if self.precision is None:
                self.precision = 0
        # Duration default
        if self.metric_type == MetricType.DURATION:
            if self.unit_of_measurement is None:
                self.unit_of_measurement = "s"
            if self.value_type is None:
                self.value_type = ValueType.INT
            if self.metric_nature == MetricNature.NONE:
                self.metric_nature = MetricNature.INSTANTANEOUS
            if self.precision is None:
                self.precision = 0
        # Cost default
        if self.metric_type == MetricType.COST:
            if self.value_type is None:
                self.value_type = ValueType.FLOAT
            if self.precision is None:
                self.precision = 2
            if self.metric_nature == MetricNature.NONE:
                self.metric_nature = MetricNature.INSTANTANEOUS
        # General initialization
        if self.value_type not in [ValueType.FLOAT, ValueType.INT_SECONDS_TO_HOURS, ValueType.INT_SECONDS_TO_MINUTES]:
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
    
    def __post_init__(self):
        self._short_id: str | None = None
        self._name: str | None = None
        self._key_values: dict[str, str] = {}

    def __repr__(self) -> str:
        """Return a string representation of the parsed topic."""
        return (
            f"ParsedTopic("
            f"installation_id={self.installation_id}, "
            f"device_id={self.device_id}, "
            f"device_type={self.device_type}, "
            # f"wildcards_with_device_type={self.wildcards_with_device_type}, "
            # f"wildcards_without_device_type={self.wildcards_without_device_type}, "
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

        if len(topic_parts) < 3:  # noqa: PLR2004"
            return None
        elif len(topic_parts) == 3 and topic_parts[2] != "heartbeat":  # noqa: PLR2004"
            return None

        installation_id = topic_parts[1]
        device_type = topic_to_device_type(topic_parts)
        wildcard_topic_parts = topic_parts.copy()
        wildcard_topic_parts[1] = "##installation_id##"
        if device_type is None: # This can happen as we register for the attribute topics so we get them for devices we dont have topics for
            _LOGGER.debug("Unknown device type for topic: %s", topic)
            # If the device type is unknown, we cannot create a ParsedTopic
            return None

        #Special handling for root topic. Currently only: N/##installation_id##/heartbeat
        if len(topic_parts) == 3:
            device_id = "0"
            wildcards_without_device_type = wildcards_with_device_type = ParsedTopic.normalize_topic("/".join(wildcard_topic_parts))
        else:
            device_id = topic_parts[3]
            wildcard_topic_parts[3] = "##device_id##"
            wildcards_with_device_type = ParsedTopic.normalize_topic("/".join(wildcard_topic_parts))
            wildcard_topic_parts[2] = "##device_type##"
            wildcards_without_device_type = ParsedTopic.normalize_topic("/".join(wildcard_topic_parts))

        return cls(
            installation_id,
            device_id,
            device_type,
            wildcards_with_device_type,
            wildcards_without_device_type,
            full_topic,
        )

    @classmethod
    def make_unique_id(cls, device_short_unique_id: str, short_id: str) -> str:
        return f"{device_short_unique_id}_{short_id}"

    def get_device_unique_id(self) -> str:
        return f"{self.device_type.code}_{self.device_id}"

    def finalize_topic_fields(self, topic_desc: TopicDescriptor) -> None:
        self._key_values = self.get_key_values(topic_desc)
        self._key_values.update(topic_desc.key_values)
        self._short_id = self._replace_ids(topic_desc.short_id)
        self._unique_id = ParsedTopic.make_unique_id(self.get_device_unique_id(), self._short_id)
        assert topic_desc.name is not None, f"TopicDescriptor name is None for topic: {topic_desc.topic}"
        self._name = self._replace_ids(topic_desc.name)

    # This is needed in cases of solarcharger_max_power_today and solarcharger_max_power_yesterday
    # which has the same topic but different meaning
    def match_from_list(self, topic_desc_list: list[TopicDescriptor]) -> TopicDescriptor |None:
        topic_parts = self.full_topic.split("/")
        topic_parts[1] = "{installation_id}"
        topic_parts[3] = "{device_id}"
        normalized_topic = "/".join(topic_parts)
        for topic_desc in topic_desc_list:
            if topic_desc.topic == normalized_topic:
                return topic_desc
        return None

    @property
    def short_id(self) -> str:
        assert self._short_id is not None, f"short_id is None for topic: {self.full_topic}"
        return self._short_id

    @property
    def unique_id(self) -> str:
        assert self._unique_id is not None, f"unique_id is None for topic: {self.full_topic}"
        return self._unique_id

    @property
    def key_values(self) -> dict[str, str]:
        assert self._key_values is not None, f"key_values is None for topic: {self.full_topic}"
        return self._key_values

    def _replace_ids(self, string: str) -> str:
        return ParsedTopic.replace_ids(string, self.key_values)

    @staticmethod
    def replace_ids(string: str, key_values: dict[str, str]) -> str:
        """Replace placeholders in the string with matched items from self.key_values."""
        import re

        def replace_match(match):
            key = match.group(1)
            if key in key_values:
                return key_values[key]
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
