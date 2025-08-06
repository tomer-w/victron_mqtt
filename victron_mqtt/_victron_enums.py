from .constants import VictronEnum

class DeviceType(VictronEnum):
    """Type of device."""
    # This is used to identify the type of device in the system.
    # BEWARE!!! The code is used for mapping from the victron topic, IT IS NOT RANDOM FREE TEXT. The string is used for display purposes.
    # For settings this will be used to identify the device type in the settings.
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
    GENERATOR = ("generator", "Generator")
    TANK = ("tank", "Liquid Tank")
    MULTI_RS_SOLAR = ("multi", "Multi RS Solar")
    CGWACS = ("CGwacs", "Carlo Gavazzi Wired AC Sensors") # Should be mapped to SYSTEM
    DC_LOAD = ("dcload", "DC Load")
    ALTERNATOR = ("alternator", "Charger (Orion/Alternator)")
    SWITCH = ("switch", "Switch")
    GPS = ("gps", "Gps")

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

class InverterOverloadAlarmEnum(VictronEnum):
    NoAlarm = (0, "No Alarm")
    Warning = (1, "Warning")
    Alarm = (2, "Alarm")

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

class FluidType(VictronEnum):
    """Fluid type enum"""
    Fuel = (0, "Fuel")
    FreshWater = (1, "Fresh Water")
    WasteWater = (2, "Waste Water")
    LiveWell = (3, "Live Well")
    Oil = (4, "Oil")
    BlackWater = (5, "Black water (sewage)")
    Gasoline = (6, "Gasoline")
    Diesel = (7, "Diesel")
    LPG = (8, "Liquid  Petroleum Gas (LPG)")
    LNG = (9, "Liquid Natural Gas (LNG)")
    HydraulicOil = (10, "Hydraulic oil")
    RawWater = (11, "Raw water")
    
class MultiState(VictronEnum):
    Off = (0, "Off")
    VoltageCurrentLimited = (1, "Voltage/current limited")
    MPPTActive = (2, "MPPT active")
    NotAvailable = (255, "Not available")

class ESSMode(VictronEnum):
    SelfConsumptionBatterylife = (0, "self consumption (batterylife)")
    SelfConsumption = (1, "self consumption")
    KeepCharged = (2, "keep charged")
    ExternalControl = (3, "External control")

class SolarChargerState(VictronEnum):
    Off = (0, "Off")
    Fault = (2, "Fault")
    Bulk = (3, "Bulk")
    Absorption = (4, "Absorption")
    Float = (5, "Float")
    Storage = (6, "Storage")
    Equalize = (7, "Equalize")
    ExternalControl = (252, "External control")