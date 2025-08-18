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

class DESSReactiveStrategy(VictronEnum):
    SCHEDULED_SELFCONSUME = (1, "Scheduled Self-Consume")
    SCHEDULED_CHARGE_ALLOW_GRID = (2, "Scheduled Charge Allow Grid")
    SCHEDULED_CHARGE_ENHANCED = (3, "Scheduled Charge Enhanced")
    SELFCONSUME_ACCEPT_CHARGE = (4, "Self-Consume Accept Charge")
    IDLE_SCHEDULED_FEEDIN = (5, "Idle Scheduled Feed-In")
    SCHEDULED_DISCHARGE = (6, "Scheduled Discharge")
    SELFCONSUME_ACCEPT_DISCHARGE = (7, "Self-Consume Accept Discharge")
    IDLE_MAINTAIN_SURPLUS = (8, "Idle Maintain Surplus")
    IDLE_MAINTAIN_TARGETSOC = (9, "Idle Maintain Target SOC")
    SCHEDULED_CHARGE_SMOOTH_TRANSITION = (10, "Scheduled Charge Smooth Transition")
    SCHEDULED_CHARGE_FEEDIN = (11, "Scheduled Charge Feed-In")
    SCHEDULED_CHARGE_NO_GRID = (12, "Scheduled Charge No Grid")
    SCHEDULED_MINIMUM_DISCHARGE = (13, "Scheduled Minimum Discharge")
    SELFCONSUME_NO_GRID = (14, "Self-Consume No Grid")
    IDLE_NO_OPPORTUNITY = (15, "Idle No Opportunity")
    UNSCHEDULED_CHARGE_CATCHUP_TARGETSOC = (16, "Unscheduled Charge Catch-Up Target SOC")
    SELFCONSUME_INCREASED_DISCHARGE = (17, "Self-Consume Increased Discharge")
    KEEP_BATTERY_CHARGED = (18, "Keep Battery Charged")
    SCHEDULED_DISCHARGE_SMOOTH_TRANSITION = (19, "Scheduled Discharge Smooth Transition")
    DESS_DISABLED = (92, "DESS Disabled")
    SELFCONSUME_UNEXPECTED_EXCEPTION = (93, "Self-Consume Unexpected Exception")
    SELFCONSUME_FAULTY_CHARGERATE = (94, "Self-Consume Faulty Charge Rate")
    UNKNOWN_OPERATING_MODE = (95, "Unknown Operating Mode")
    ESS_LOW_SOC = (96, "ESS Low SOC")
    SELFCONSUME_UNMAPPED_STATE = (97, "Self-Consume Unmapped State")
    SELFCONSUME_UNPREDICTED = (98, "Self-Consume Unpredicted")
    NO_WINDOW = (99, "No Window")

class DESSStrategy(VictronEnum):
    TARGETSOC = (0, "Target SOC")
    SELFCONSUME = (1, "Self-Consume")
    PROBATTERY = (2, "Pro Battery")
    PROGRID = (3, "Pro Grid")

class DESSErrorCode(VictronEnum):
    NO_ERROR = (0,"No Error")
    NO_ESS = (1,"No ESS")
    ESS_MODE = (2, "ESS Mode") # ???
    NO_SCHEDULE = (3, "No Matching Schedule")
    SOC_LOW = (4, "SOC low")
    BATTRY_CAPACITY_NOT_CONFIGURED = (5,"Battery Capacity Not Configured")

class DESSRestrictions(VictronEnum):
    NO_RESTRICTIONS = (0, "No Restrictions between battery and the grid")
    GRID_TO_BATTERY_RESTRICTED = (1, "Grid to battey energy flow restricted")
    BATTERY_TO_GRID_RESTRICTED = (2, "Battery to grid energy flow restricted")
    NO_FLOW = (3, "No energy flow between battery and grid")
