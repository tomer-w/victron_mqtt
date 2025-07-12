"""Constants for the victron venus OS client."""

from enum import Enum
from typing import TypeVar, cast

TOPIC_INSTALLATION_ID = "N/+/system/0/Serial"


class MetricKind(Enum):
    """Type of MQTT message."""

    ATTRIBUTE = "attribute"
    SENSOR = "sensor"
    BINARY_SENSOR = "binary_sensor"
    SWITCH = "switch"
    SELECT = "select"
    NUMBER = "number"


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
    ENERGY = "energy"
    VOLTAGE = "voltage"
    CURRENT = "current"
    TEMPERATURE = "temperature"
    PRESSURE = "pressure"
    FREQUENCY = "frequency"
    TIME = "time"
    PERCENTAGE = "percentage"
    ELECTRIC_STORAGE_CAPACITY = "electric_storage_capacity"


class ValueType(Enum):
    """Value types."""

    INT = "int"
    INT_DEFAULT_0 = "int_0"
    FLOAT = "float"
    STRING = "str"
    ENUM = "enum"

PLACEHOLDER_PHASE = "{phase}"

T = TypeVar("T", bound="VictronEnum")
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
    def from_code(cls: type[T], value: int | str, default_value: T | None = None) -> T | None:
        lookup = cls._build_code_lookup()
        result = lookup.get(value, default_value)
        return cast(T, result) if result is not None else None

    @classmethod
    def _build_string_lookup(cls):
        if not hasattr(cls, '_lookup_by_string'):
            cls._lookup_by_string = {member.string: member for member in cls}
        return cls._lookup_by_string

    @classmethod
    def from_string(cls, value: str):
        lookup = cls._build_string_lookup()
        try:
            return lookup[value]
        except KeyError:
            raise ValueError(f"No enum member found with string={value}")
