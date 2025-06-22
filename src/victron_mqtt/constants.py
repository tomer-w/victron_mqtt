"""Constants for the victron venus OS client."""

from enum import Enum

TOPIC_INSTALLATION_ID = "N/+/system/0/Serial"


class MessageType(Enum):
    """Type of MQTT message."""

    ATTRIBUTE = "attribute"
    METRIC = "metric"


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


PLACEHOLDER_PHASE = "{phase}"

DEFAULT_HOST = "venus.local."
DEFAULT_PORT = 1883
