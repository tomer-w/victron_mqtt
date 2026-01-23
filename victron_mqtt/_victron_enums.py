"""Victron Enums Module."""
from .constants import VictronDeviceEnum, VictronEnum

class DeviceType(VictronDeviceEnum):
    """Type of device."""
    # This is used to identify the type of device in the system.
    # BEWARE!!! The code is used for mapping from the victron topic, IT IS NOT RANDOM FREE TEXT. The string is used for display purposes.
    # For settings this will be used to identify the device type in the settings.
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
    GENERATOR0 = ("Generator0", "Generator 0 Settings")
    GENERATOR1 = ("Generator1", "Generator 1 Settings")
    TANK = ("tank", "Liquid Tank")
    MULTI_RS_SOLAR = ("multi", "Multi RS Solar")
    CGWACS = ("CGwacs", "<Not used>", "system") # Should be mapped to SYSTEM
    DC_LOAD = ("dcload", "DC Load")
    ALTERNATOR = ("alternator", "Charger (Orion/Alternator)")
    SWITCH = ("switch", "Switch")
    GPS = ("gps", "Gps")
    SYSTEM_SETUP = ("SystemSetup", "System Setup")
    TRANSFER_SWITCH = ("TransferSwitch", "Transfer Switch")
    DIGITAL_INPUT = ("digitalinput", "Digital Input")
    DC_SYSTEM = ("dcsystem", "DC System")
    RELAY = ("Relay", "<Not used>", "system") # Should be mapped to SYSTEM
    PLATFORM = ("platform", "Platform", "system") # For whatever reason some system topics are under platform
    HEATPUMP = ("heatpump", "Heat Pump")
    DYNAMIC_ESS = ("DynamicEss", "Dynamic ESS", "system") # Dynamic ESS settings are under system
    ACLOAD = ("acload", "AC Load")
    HUB4 = ("hub4", "Hub4")


class GenericOnOff(VictronEnum):
    """On/Off Enum"""
    OFF = (0, "Off")
    ON = (1, "On")

class ChargerMode(VictronEnum):
    """Charger Mode Enum"""
    ON = (1, "On")
    OFF = (4, "Off")

class InverterMode(VictronEnum):
    """Inverter Mode Enum"""
    CHARGER_ONLY = (1, "Charger Only")
    INVERTER_ONLY = (2, "Inverter Only")
    ON = (3, "On")
    OFF = (4, "Off")

class PhoenixInverterMode(VictronEnum):
    """Inverter Mode Enum"""
    INVERTER = (2, "Inverter")
    OFF = (4, "Off")
    ECO = (5, "Eco")

class State(VictronEnum):
    """State Enum"""
    OFF = (0, "Off")
    LOW_POWER = (1, "Low Power")
    FAULT = (2, "Fault")
    BULK = (3, "Bulk")
    ABSORPTION = (4, "Absorption")
    FLOAT = (5, "Float")
    STORAGE = (6, "Storage")
    EQUALIZE = (7, "Equalize")
    PASSTHROUGH = (8, "Passthrough")
    INVERTING = (9, "Inverting")
    POWER_ASSIST = (10, "Power Assist")
    POWER_SUPPLY = (11, "Power Supply")
    SUSTAIN = (244, "Sustain")
    STARTING_UP = (245, "Starting Up")
    REPEATED_ABSORPTION = (246, "Repeated Absorption")
    AUTO_EQUALIZE = (247, "Auto Equalize / Recondition")
    BATTERY_SAFE = (248, "Battery Safe")
    EXTERNAL_CONTROL = (252, "External Control")
    DISCHARGING = (256, "Discharging")
    SUSTAIN_ALT = (257, "Sustain Alt")
    RECHARGING = (258, "Recharging")
    SCHEDULED_RECHARGING = (259, "Scheduled Recharging")

class GenericAlarmEnum(VictronEnum):
    """Generic Alarm Enum"""
    NO_ALARM = (0, "No Alarm")
    WARNING = (1, "Warning")
    ALARM = (2, "Alarm")

class EvChargerMode(VictronEnum):
    """EVCharger Mode Enum"""
    MANUAL = (0, "Manual")
    AUTO = (1, "Auto")
    SCHEDULED_CHARGE = (2, "Scheduled Charge")

class EvChargerPosition(VictronEnum):
    """EVCharger Position Enum"""
    AC_OUT = (0, "AC Out")
    AC_INPUT = (1, "AC Input")

class EvChargerStatus(VictronEnum):
    """EVCharger Status Enum"""
    DISCONNECTED = (0, "Disconnected")
    CONNECTED = (1, "Connected")
    CHARGING = (2, "Charging")
    CHARGED = (3, "Charged")
    WAITING_FOR_SUN = (4, "Waiting for sun")
    WAITING_FOR_RFID = (5, "Waiting for RFID")
    WAITING_FOR_START = (6, "Waiting for start")
    LOW_SOC = (7, "Low SOC")
    GROUND_TEST_ERROR = (8, "Ground test error")
    WELDED_CONTACTS_TEST_ERROR = (9, "Welded contacts test error")
    CP_INPUT_TEST_ERROR= (10, "CP input test error")
    RESIDUAL_CURRENT_DETECTED = (11, "Residual current detected")
    UNDERVOLTAGE_DETECTED = (12, "Undervoltage detected")
    OVERVOLTAGE_DETECTED = (13, "Overvoltage detected")
    OVERHEATING_DETECTED = (14, "Overheating detected")
    RESERVED15 = (15, "Reserved")
    RESERVED16 = (16, "Reserved")
    RESERVED17 = (17, "Reserved")
    RESERVED18 = (18, "Reserved")
    RESERVED19 = (19, "reserved")
    CHARGING_LIMIT = (20, "Charging limit")
    START_CHARGING = (21, "Start charging")
    SWITCHING_TO_3_PHASE = (22, "Switching to 3 phase")
    SWITCHING_TO_1_PHASE = (23, "Switching to 1 phase")

class TemperatureStatus(VictronEnum):
    """Temperature sensor status enum"""
    OK = (0, "Ok")
    DISCONNECTED = (1, "Disconnected")
    SHORT_CIRCUITED = (2, "Short circuited")
    REVERSE_POLARITY = (3, "Reverse polarity")
    UNKNOWN = (4, "Unknown")

class TemperatureType(VictronEnum):
    """Temperature sensor type enum"""
    BATTERY = (0, "Battery")
    FRIDGE = (1, "Fridge")
    GENERIC = (2, "Generic")
    ROOM = (3, "Room")
    OUTDOOR = (4, "Outdoor")
    WATER_HEATER = (5, "Water Heater")
    FREEZER = (6, "Freezer")

class FluidType(VictronEnum):
    """Fluid type enum"""
    FUEL = (0, "Fuel")
    FRESH_WATER = (1, "Fresh Water")
    WASTE_WATER = (2, "Waste Water")
    LIVE_WELL = (3, "Live Well")
    OIL = (4, "Oil")
    BLACK_WATER = (5, "Black water (sewage)")
    GASOLINE = (6, "Gasoline")
    DIESEL = (7, "Diesel")
    LPG = (8, "Liquid  Petroleum Gas (LPG)")
    LNG = (9, "Liquid Natural Gas (LNG)")
    HYDRAULIC_OIL = (10, "Hydraulic oil")
    RAW_WATER = (11, "Raw water")

class MppOperationMode(VictronEnum):
    """MPP Operation Mode Enum"""
    OFF = (0, "Off")
    VOLTAGE_CURRENT_LIMITED = (1, "Voltage/current limited")
    MPPT_ACTIVE = (2, "MPPT active")
    NOT_AVAILABLE = (255, "Not available")

class ESSMode(VictronEnum):
    """ESS Mode Enum"""
    SELF_CONSUMPTION_BATTERYLIFE = (0, "self consumption (batterylife)")
    SELF_CONSUMPTION = (1, "self consumption")
    KEEP_CHARGED = (2, "keep charged")
    EXTERNAL_CONTROL = (3, "External control")

class GeneratorRunningByConditionCode(VictronEnum):
    """Generator Running By Condition Code Enum"""
    STOPPED = (0, "Stopped")
    MANUAL = (1, "Manual")
    TEST_RUN = (2, "Test Run")
    LOST_COMMS = (3, "Lost Comms")
    SOC = (4, "SOC")
    AC_LOAD = (5, "AC Load")
    BATTERY_CURRENT = (6, "Battery Current")
    BATTERY_VOLTS = (7, "Battery Volts")
    INV_TEMP = (8, "Inv Temp")
    INV_OVERLOAD = (9, "Inv Overload")
    STOP_ON_AC1 = (10, "Stop On AC1")

class DESSReactiveStrategy(VictronEnum):
    """DESS Reactive Strategy Enum"""
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
    """DESS Strategy Enum"""
    TARGETSOC = (0, "Target SOC")
    SELFCONSUME = (1, "Self-Consume")
    PROBATTERY = (2, "Pro Battery")
    PROGRID = (3, "Pro Grid")

class DESSErrorCode(VictronEnum):
    """DESS Error Code Enum"""
    NO_ERROR = (0,"No Error")
    NO_ESS = (1,"No ESS")
    ESS_MODE = (2, "ESS Mode") # ???
    NO_SCHEDULE = (3, "No Matching Schedule")
    SOC_LOW = (4, "SOC low")
    BATTRY_CAPACITY_NOT_CONFIGURED = (5,"Battery Capacity Not Configured")

class DESSMode(VictronEnum):
    """DESS Mode Enum"""
    OFF = (0, "Off")
    AUTO_VRM = (1, "Auto / VRM")
    BUY = (2, "Buy")
    SELL = (3, "Sell")
    NODE_RED = (4, "Node-RED")

class DESSRestrictions(VictronEnum):
    """DESS Restrictions Enum"""
    NO_RESTRICTIONS = (0, "No Restrictions between battery and the grid")
    BATTERY_TO_GRID_RESTRICTED = (1, "Battery to grid energy flow restricted")
    GRID_TO_BATTERY_RESTRICTED = (2, "Grid to battery energy flow restricted")
    NO_FLOW = (3, "No energy flow between battery and grid")

class ErrorCode(VictronEnum):
    """Generic Error Code Enum"""
    NO_ERROR = (0, "No error")
    BATTERY_VOLTAGE_TOO_HIGH = (2, "Battery voltage too high")
    CHARGER_TEMPERATURE_TOO_HIGH = (17, "Charger temperature too high")
    CHARGER_OVER_CURRENT = (18, "Charger over current")
    CHARGER_CURRENT_REVERSED = (19, "Charger current reversed")
    BULK_TIME_LIMIT_EXCEEDED = (20, "Bulk time limit exceeded")
    CURRENT_SENSOR_ISSUE = (21, "Current sensor issue")
    TERMINALS_OVERHEATED = (26, "Terminals overheated")
    CONVERTER_ISSUE = (28, "Converter issue")
    INPUT_VOLTAGE_TOO_HIGH = (33, "Input voltage too high (solar panel)")
    INPUT_CURRENT_TOO_HIGH = (34, "Input current too high (solar panel)")
    INPUT_SHUTDOWN_BATTERY_VOLTAGE_TOO_HIGH = (38, "Input shutdown (battery voltage too high)")
    INPUT_SHUTDOWN_REVERSE_CURRENT = (39, "Input shutdown (reverse current)")
    LOST_COMMUNICATION_WITH_DEVICE = (65, "Lost communication with device")
    SYNCHRONIZED_CHARGING_CONFIG_ISSUE = (66, "Synchronized charging config issue")
    BMS_CONNECTION_LOST = (67, "BMS connection lost")
    NETWORK_MISCONFIGURED = (68, "Network misconfigured")
    FACTORY_CALIBRATION_DATA_LOST = (116, "Factory calibration data lost")
    INVALID_INCOMPATIBLE_FIRMWARE = (117, "Invalid/incompatible firmware")
    USER_SETTINGS_INVALID = (119, "User settings invalid")

class DigitalInputInputState(VictronEnum):
    """Raw input state: High/Open (0) or Low/Closed (1)."""
    HIGH_OPEN = (0, "High/Open")
    LOW_CLOSED = (1, "Low/Closed")

class DigitalInputType(VictronEnum):
    """Type of digital input."""
    DISABLED = (0, "Disabled")
    PULSE_METER = (1, "Pulse meter")
    DOOR_ALARM = (2, "Door alarm")
    BILGE_PUMP = (3, "Bilge pump")
    BILGE_ALARM = (4, "Bilge alarm")
    BURGLAR_ALARM = (5, "Burglar alarm")
    SMOKE_ALARM = (6, "Smoke alarm")
    FIRE_ALARM = (7, "Fire alarm")
    CO2_ALARM = (8, "CO2 alarm")
    GENERATOR = (9, "Generator")
    TOUCH_INPUT_CONTROL = (10, "Touch input control")

class DigitalInputState(VictronEnum):
    """Translated input state (determined by input type)."""
    LOW = (0, "Low")
    HIGH = (1, "High")
    OFF = (2, "Off")
    ON = (3, "On")
    NO = (4, "No")
    YES = (5, "Yes")
    OPEN = (6, "Open")
    CLOSED = (7, "Closed")
    OK = (8, "Ok")
    ALARM = (9, "Alarm")
    RUNNING = (10, "Running")
    STOPPED = (11, "Stopped")

class ESSState(VictronEnum):
    """ESS State Enum"""
    #Optimized mode with BatteryLife:
    # 1 is Value set by the GUI when BatteryLife is enabled. Hub4Control uses it to find the right BatteryLife state (values 2-7) based on system state
    WITH_BATTERY_LIFE = (1, "Optimized mode with BatteryLife")
    SELF_CONSUMPTION = (2, "Self consumption")
    SELF_CONSUMPTION_SOC_EXCEEDS_85= (3, "Self consumption, SoC exceeds 85%")
    SELF_CONSUMPTION_SOC_AT_100 = (4, "Self consumption, SoC at 100%")
    SOC_BELOW_BATTERY_LIFE_DYNAMIC_SOC_LIMIT = (5, "SoC below BatteryLife dynamic SoC limit")
    SOC_BELOW_SOC_LIMIT_24_HOURS = (6, "SoC has been below SoC limit for more than 24 hours. Charging with battery with 5amps")
    SUSTAIN = (7, "Multi/Quattro is in sustain")
    RECHARGE = (8, "Recharge, SOC dropped 5% or more below MinSOC")
    #Keep batteries charged mode:
    KEEP_BATTERIES_CHARGED = (9, "'Keep batteries charged' mode enabled")
    #Optimized mode without BatteryLife:
    SELF_CONSUMPTION_SOC_ABOVE_MIN = (10, "Self consumption, SoC at or above minimum SoC")
    SELF_CONSUMPTION_SOC_BELOW_MIN = (11, "Self consumption, SoC is below minimum SoC")
    RECHARGE_NO_BATTERY_LIFE = (12, "Recharge, SOC dropped 5% or more below MinSOC (No BatteryLife)")

class ESSModeHub4(VictronEnum):
    """ESS Mode Enum for Hub4Control"""
    PHASE_COMPENSATION_ENABLED = (1, "Optimized mode or 'keep batteries charged' and phase compensation enabled")
    PHASE_COMPENSATION_DISABLED = (2, "Optimized mode or 'keep batteries charged' and phase compensation disabled")
    EXTERNAL_CONTROL = (3, "External control")

class AcActiveInputSource(VictronEnum):
    """AC Active Input Source Enum"""
    UNKNOWN = (0, "Unknown")
    GRID = (1, "Grid")
    GENERATOR = (2, "Generator")
    SHORE_POWER = (3, "Shore power")
    NOT_CONNECTED = (240, "Not connected")

class ChargeSchedule(VictronEnum):
    """Charge Schedule Enum"""
    DISABLED_SUNDAY= (-10, "Disabled (Sunday)")
    DISABLED_WEEKEND= (-9, "Disabled (Weekends)")
    DISABLED_WEEKDAYS= (-8, "Disabled (Weekdays)")
    DISABLED_EVERY_DAY= (-7, "Disabled (Every day)")
    DISABLED_SATURDAY= (-6, "Disabled (Saturday)")
    DISABLED_FRIDAY= (-5, "Disabled (Friday)")
    DISABLED_THURSDAY= (-4, "Disabled (Thursday)")
    DISABLED_WEDNESDAY= (-3, "Disabled (Wednesday)")
    DISABLED_TUESDAY= (-2, "Disabled (Tuesday)")
    DISABLED_MONDAY= (-1, "Disabled (Monday)")
    SUNDAY = (0, "Sunday")
    MONDAY = (1, "Monday")
    TUESDAY = (2, "Tuesday")
    WEDNESDAY = (3, "Wednesday")
    THURSDAY = (4, "Thursday")
    FRIDAY = (5, "Friday")
    SATURDAY = (6, "Saturday")
    EVERY_DAY = (7, "Every day")
    WEEKDAYS = (8, "Weekdays")
    WEEKENDS = (9, "Weekends")

class ActiveInputEnum(VictronEnum):
    """Active Input Enum"""
    AC_INPUT_1 = (0, "AC Input 1")
    AC_INPUT_2 = (1, "AC Input 2")
    DISCONNECTED = (240, "Disconnected")

class SolarChargerDeviceOffReason(VictronEnum):
    """Solar Charger Device Off Reason Enum"""
    NONE = (0x00, "-")
    NO_INPUT_POWER = (0x01, "No/Low input power")
    SWITCHED_OFF_POWER_SWITCH = (0x02, "Switched off (power switch)")
    SWITCHED_OFF_DEVICE_MODE_REGISTER = (0x04, "Switched off (device mode register)")
    REMOTE_INPUT = (0x08, "Remote input")
    PROTECTIVE_ACTION = (0x10, "Protection active")
    NEED_TOKEN = (0x20, "Need token for operation")
    SIGNAL_FROM_BMS = (0x40, "Signal from BMS")
    ENGINE_SHUTDOWN = (0x80, "Engine shutdown on low input voltage")
    ANALYSING_INPUT_VOLTAGE = (0x100, "Analysing input voltage")
    LOW_TEMPERATURE = (0x200, "Low temperature")
    NO_PANEL_POWER = (0x400, "No/Low panel power")
    NO_BATTERY_POWER = (0x800, "No/Low battery power")
    ACTIVE_ALARM = (0x8000, "Active alarm")
