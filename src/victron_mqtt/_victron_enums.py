from .constants import VictronEnum

class DeviceType(VictronEnum):
    """Type of device."""

    UNKNOWN = ("unknown", "Unknown Device")
    SYSTEM = ("system", "System")
    SOLAR_CHARGER = ("solarcharger", "Solar Charger")
    INVERTER = ("inverter", "Inverter")
    BATTERY = ("battery", "Battery")
    GRID = ("grid", "Grid")
    VEBUS = ("vebus", "VE.Bus")
    EVCHARGER = ("evcharger", "EV Charging Station")
    PVINVERTER = ("pvinverter", "PV Inverter")
    TEMPERATURE = ("temperature", "Temperature")

class GenericOnOff(VictronEnum):
    """On/Off  Enum"""
    Off = (0, "Off")
    On = (1, "On")

class InverterMode(VictronEnum):
    """Inverter Mode Enum"""
    ChargerOnly = (1, "Charger Only")
    InverterOnly = (2, "Inverter Only")
    On = (3, "On")
    Off = (4, "Off")

class InverterState(VictronEnum):
    """Inverter State Enum"""
    Off = (0, "Off")
    LowPower = (1, "Low Power")
    Fault = (2, "Fault")
    Bulk = (3, "Bulk")
    Absorption = (4, "Absorption")
    Float = (5, "Float")
    Storage = (6, "Storage")
    Equalize = (7, "Equalize")
    Passthrough = (8, "Passthrough")
    Inverting = (9, "Inverting")
    PowerAssist = (10, "Power Assist")
    PowerSupply = (11, "Power Supply")
    Sustain = (244, "Sustain")
    ExternalControl = (252, "External Control")

class EvChargerMode(VictronEnum):
    """EVCharger Mode Enum"""
    Manual = (0, "Manual")
    Auto = (1, "Auto")
    ScheduledCharge = (2, "Scheduled Charge")

class TemperatureStatus(VictronEnum):
    """Temperature sensor status enum"""
    Ok = (0, "Ok")
    Disconnected = (1, "Disconnected")
    ShortCircuited = (2, "Short circuited")
    ReversePolarity = (3, "Reverse polarity")
    Unknown = (4, "Unknown")

class TemperatureType(VictronEnum):
    """Temperature sensor type enum"""
    Battery = (0, "Battery")
    Fridge = (1, "Fridge")
    Generic = (2, "Generic")
    Room = (3, "Room")
    Outdoor = (4, "Outdoor")
    WaterHeater = (5, "Water Heater")
    Freezer = (6, "Freezer")
