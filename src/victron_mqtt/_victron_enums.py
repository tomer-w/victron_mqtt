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

class EvChargerMode(VictronEnum):
    """EVCharger Mode Enum"""
    Manual = (0, "Manual")
    Auto = (1, "Auto")
    ScheduledCharge = (2, "Scheduled Charge")
