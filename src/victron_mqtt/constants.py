"""Constants for the victron venus OS client."""

from enum import Enum

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


class DeviceType(Enum):
    """Type of device."""

    ANY = "any"
    SYSTEM = "system"
    SOLAR_CHARGER = "solarcharger"
    INVERTER = "inverter"
    BATTERY = "battery"
    GRID = "grid"
    VEBUS = "vebus"
    EVCHARGER = "evcharger"


class ValueType(Enum):
    """Value types."""

    INT = "int"
    INT_DEFAULT_0 = "int_0"
    FLOAT = "float"
    STRING = "str"
    ENUM = "enum"

PLACEHOLDER_PHASE = "{phase}"

class GenericOnOff(Enum):
    """On/Off  Enum"""
    Off = 0
    On = 1

class InverterMode(Enum):
    """Inverter Mode Enum"""
    ChargerOnly = 1
    InverterOnly = 2
    On = 3
    Off = 4

class EvChargerMode(Enum):
    """EVCharger Mode Enum"""
    Manual = 0
    Auto = 1
    ScheduledCharge = 2
