"""Constants for the victron venus OS client."""

from enum import Enum
from typing import NamedTuple, Self

from dataclasses import dataclass

TOPIC_INSTALLATION_ID = "N/+/system/0/Serial"


class MetricKind(Enum):
    """Type of MQTT message."""

    ATTRIBUTE = "attribute"
    SENSOR = "sensor"
    BINARY_SENSOR = "binary_sensor"
    SWITCH = "switch"
    SELECT = "select"
    NUMBER = "number"
    SERVICE = "service"


class MetricNature(Enum):
    """Nature of the metric."""

    NONE = "none"
    INSTANTANEOUS = "instantaneous"
    CUMULATIVE = "cumulative"
    DELTA = "delta"


class MetricType(Enum):
    """The type of metric."""

    NONE = "none"
    POWER = "power"
    APPARENT_POWER = "apparent_power"
    ENERGY = "energy"
    VOLTAGE = "voltage"
    CURRENT = "current"
    TEMPERATURE = "temperature"
    PRESSURE = "pressure"
    FREQUENCY = "frequency"
    TIME = "time"
    PERCENTAGE = "percentage"
    ELECTRIC_STORAGE_CAPACITY = "electric_storage_capacity"
    ELECTRIC_STORAGE_PERCENTAGE = "electric_storage_percentage"
    LIQUID_VOLUME = "liquid_volume"
    LOCATION = "location"
    HEADING = "heading"
    SPEED = "speed"


class ValueType(Enum):
    """Value types."""

    BOOL = "bool"
    INT = "int"
    INT_DEFAULT_0 = "int_0"
    FLOAT = "float"
    STRING = "str"
    ENUM = "enum"
    EPOCH = "epoch"
    INT_SECONDS_TO_HOURS = "int_seconds_to_hours"

class RangeType(Enum):
    """Range types for numeric values."""
    STATIC = "static"  # Static range, e.g., fixed values
    DYNAMIC = "dynamic"  # Dynamic range, e.g., depends on device model

class OperationMode(Enum):
    """Enum for operation modes."""
    READ_ONLY = "read_only"
    FULL = "full"
    EXPERIMENTAL = "experimental"

@dataclass
class FormulaTransientState:
    pass

@dataclass
class FormulaPersistentState:
    pass

PLACEHOLDER_PHASE = "{phase}"
PLACEHOLDER_NEXT_PHASE = "{next_phase}"

class VictronEnum(Enum):
    def __init__(self, code, string):
        self._value_ = (code, string)
        self.code = code
        self.string = string

    def __repr__(self):
        return f"{self.__class__.__name__}.{self.name}(code={self.code}, string={self.string})"
    
    def __str__(self) -> str:
        return self.string

    @classmethod
    def _build_code_lookup(cls):
        if not hasattr(cls, '_lookup_by_code'):
            cls._lookup_by_code = {member.code: member for member in cls}
        return cls._lookup_by_code

    @classmethod
    def from_code(cls: type[Self], value: int | str, default_value: "VictronEnum | None" = None) -> Self | None:
        lookup = cls._build_code_lookup()
        result = lookup.get(value, default_value)
        return result  # type: ignore[return-value]

    @classmethod
    def _build_string_lookup(cls):
        if not hasattr(cls, '_lookup_by_string'):
            cls._lookup_by_string = {member.string: member for member in cls}
        return cls._lookup_by_string

    @classmethod
    def from_string(cls: type[Self], value: str) -> Self:
        lookup = cls._build_string_lookup()
        try:
            return lookup[value]
        except KeyError:
            raise ValueError(f"No enum member found with string={value}")

class VictronDeviceEnum(VictronEnum):
    def __init__(self, code: str, string: str, mapped_to: str | None = None):
        super().__init__(code, string)
        self.mapped_to = mapped_to

    @classmethod
    def from_code(cls: type[Self], value: int | str, default_value: "VictronDeviceEnum | None" = None) -> "VictronDeviceEnum | None":
        result = super().from_code(value, default_value)
        if result is None:
            return None
        assert isinstance(result, VictronDeviceEnum)
        if result.mapped_to:
            mapped_result = super().from_code(result.mapped_to, default_value)
            if mapped_result is None:
                return None
            assert isinstance(mapped_result, VictronDeviceEnum)
            result = mapped_result
        return result
