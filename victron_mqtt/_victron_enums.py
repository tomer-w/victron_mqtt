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


class GenericOnOff(VictronEnum):
    """On/Off Enum"""
    Off = (0, "Off")
    On = (1, "On")

class ChargerMode(VictronEnum):
    """Charger Mode Enum"""
    On = (1, "On")
    Off = (4, "Off")

class InverterMode(VictronEnum):
    """Inverter Mode Enum"""
    ChargerOnly = (1, "Charger Only")
    InverterOnly = (2, "Inverter Only")
    On = (3, "On")
    Off = (4, "Off")

class PhoenixInverterMode(VictronEnum):
    """Inverter Mode Enum"""
    INVERTER = (2, "Inverter")
    OFF = (4, "Off")
    ECO = (5, "Eco")

class State(VictronEnum):
    """State Enum"""
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
    StartingUp = (245, "Starting Up")
    RepeatedAbsorption = (246, "Repeated Absorption")
    AutoEqualize = (247, "Auto Equalize / Recondition")
    BatterySafe = (248, "Battery Safe")
    ExternalControl = (252, "External Control")
    Discharging = (256, "Discharging")
    SustainAlt = (257, "Sustain Alt")
    Recharging = (258, "Recharging")
    ScheduledRecharging = (259, "Scheduled Recharging")

class GenericAlarmEnum(VictronEnum):
    NoAlarm = (0, "No Alarm")
    Warning = (1, "Warning")
    Alarm = (2, "Alarm")

class EvChargerMode(VictronEnum):
    """EVCharger Mode Enum"""
    Manual = (0, "Manual")
    Auto = (1, "Auto")
    ScheduledCharge = (2, "Scheduled Charge")

class EvChargerPosition(VictronEnum):
    """EVCharger Position Enum"""
    AcOut = (0, "AC Out")
    AcInput = (1, "AC Input")

class EvChargerStatus(VictronEnum):
    """EVCharger Status Enum"""
    Disconnected = (0, "Disconnected")
    Connected = (1, "Connected")
    Charging = (2, "Charging")
    Charged = (3, "Charged")
    WaitingForSun = (4, "Waiting for sun")
    WaitingForRFID = (5, "Waiting for RFID")
    WaitingForStart = (6, "Waiting for start")
    LowSoc = (7, "Low SOC")
    GroundTestError = (8, "Ground test error")
    WeldedContactsTestError = (9, "Welded contacts test error")
    CPInputTestError= (10, "CP input test error")
    ResidualCurrentDetected = (11, "Residual current detected")
    UndervoltageDetected = (12, "Undervoltage detected")
    OvervoltageDetected = (13, "Overvoltage detected")
    OverheatingDetected = (14, "Overheating detected")
    Reserved15 = (15, "Reserved")
    Reserved16 = (16, "Reserved")
    Reserved17 = (17, "Reserved")
    Reserved18 = (18, "Reserved")
    Reserved19 = (19, "reserved")
    ChargingLimit = (20, "Charging limit")
    StartCharging = (21, "Start charging")
    SwitchingTo3Phase = (22, "Switching to 3 phase")
    SwitchingTo1Phase = (23, "Switching to 1 phase")

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
    
class MppOperationMode(VictronEnum):
    Off = (0, "Off")
    VoltageCurrentLimited = (1, "Voltage/current limited")
    MPPTActive = (2, "MPPT active")
    NotAvailable = (255, "Not available")

class ESSMode(VictronEnum):
    SelfConsumptionBatterylife = (0, "self consumption (batterylife)")
    SelfConsumption = (1, "self consumption")
    KeepCharged = (2, "keep charged")
    ExternalControl = (3, "External control")

class GeneratorRunningByConditionCode(VictronEnum):
    Stopped = (0, "Stopped")
    Manual = (1, "Manual")
    TestRun = (2, "Test Run")
    LostComms = (3, "Lost Comms")
    SOC = (4, "SOC")
    ACLoad = (5, "AC Load")
    BatteryCurrent = (6, "Battery Current")
    BatteryVolts = (7, "Battery Volts")
    InvTemp = (8, "Inv Temp")
    InvOverload = (9, "Inv Overload")
    StopOnAC1 = (10, "Stop On AC1")

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

class DESSMode(VictronEnum):
    """DESS Mode Enum"""
    OFF = (0, "Off")
    AUTO_VRM = (1, "Auto / VRM")
    BUY = (2, "Buy")
    SELL = (3, "Sell")
    NODE_RED = (4, "Node-RED")

class DESSRestrictions(VictronEnum):
    NO_RESTRICTIONS = (0, "No Restrictions between battery and the grid")
    BATTERY_TO_GRID_RESTRICTED = (1, "Battery to grid energy flow restricted")
    GRID_TO_BATTERY_RESTRICTED = (2, "Grid to battery energy flow restricted")
    NO_FLOW = (3, "No energy flow between battery and grid")

class ErrorCode(VictronEnum):
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
    High_Open = (0, "High/Open")
    Low_Closed = (1, "Low/Closed")

class DigitalInputType(VictronEnum):
    """Type of digital input."""
    Disabled = (0, "Disabled")
    PulseMeter = (1, "Pulse meter")
    DoorAlarm = (2, "Door alarm")
    BilgePump = (3, "Bilge pump")
    BilgeAlarm = (4, "Bilge alarm")
    BurglarAlarm = (5, "Burglar alarm")
    SmokeAlarm = (6, "Smoke alarm")
    FireAlarm = (7, "Fire alarm")
    CO2Alarm = (8, "CO2 alarm")
    Generator = (9, "Generator")
    TouchInputControl = (10, "Touch input control")

class DigitalInputState(VictronEnum):
    """Translated input state (determined by input type)."""
    Low = (0, "Low")
    High = (1, "High")
    Off = (2, "Off")
    On = (3, "On")
    No = (4, "No")
    Yes = (5, "Yes")
    Open = (6, "Open")
    Closed = (7, "Closed")
    Ok = (8, "Ok")
    Alarm = (9, "Alarm")
    Running = (10, "Running")
    Stopped = (11, "Stopped")
    
class ESSState(VictronEnum):
    #Optimized mode with BatteryLife:
    # 1 is Value set by the GUI when BatteryLife is enabled. Hub4Control uses it to find the right BatteryLife state (values 2-7) based on system state
    WithBatteryLife = (1, "Optimized mode with BatteryLife")
    SelfConsumption = (2, "Self consumption")
    SelfConsumptionSoCExceeds85= (3, "Self consumption, SoC exceeds 85%")
    SelfConsumptionSoCat100 = (4, "Self consumption, SoC at 100%")
    SoCBelowBatteryLifeDynamicSoClimit = (5, "SoC below BatteryLife dynamic SoC limit")
    SoCBelowSoCLimit24Hours = (6, "SoC has been below SoC limit for more than 24 hours. Charging with battery with 5amps")
    Sustain = (7, "Multi/Quattro is in sustain")
    Recharge = (8, "Recharge, SOC dropped 5% or more below MinSOC")
    #Keep batteries charged mode:
    KeepBatteriesCharged = (9, "'Keep batteries charged' mode enabled")
    #Optimized mode without BatteryLife:
    SelfConsumptionSoCAboveMin = (10, "Self consumption, SoC at or above minimum SoC")
    SelfConsumptionSoCBelowMin = (11, "Self consumption, SoC is below minimum SoC")
    RechargeNoBatteryLife = (12, "Recharge, SOC dropped 5% or more below MinSOC (No BatteryLife)")

class ESSModeHub4(VictronEnum):
    PhaseCompensationEnabled = (1, "Optimized mode or 'keep batteries charged' and phase compensation enabled")
    PhaseCompensationDisabled = (2, "Optimized mode or 'keep batteries charged' and phase compensation disabled")
    ExternalControl = (3, "External control")

class AcActiveInputSource(VictronEnum):
    """AC Active Input Source Enum"""
    Unknown = (0, "Unknown")
    Grid = (1, "Grid")
    Generator = (2, "Generator")
    ShorePower = (3, "Shore power")
    NotConnected = (240, "Not connected")

class ChargeSchedule(VictronEnum):
    """Charge Schedule Enum"""
    DisabledSunday= (-10, "Disabled (Sunday)")
    DisabledWeekend= (-9, "Disabled (Weekends)")
    DisabledWeekdays= (-8, "Disabled (Weekdays)")
    DisabledEveryDay= (-7, "Disabled (Every day)")
    DisabledSaturday= (-6, "Disabled (Saturday)")
    DisabledFriday= (-5, "Disabled (Friday)")
    DisabledThursday= (-4, "Disabled (Thursday)")
    DisabledWednesday= (-3, "Disabled (Wednesday)")
    DisabledTuesday= (-2, "Disabled (Tuesday)")
    DisabledMonday= (-1, "Disabled (Monday)")
    Sunday = (0, "Sunday")
    Monday = (1, "Monday")
    Tuesday = (2, "Tuesday")
    Wednesday = (3, "Wednesday")
    Thursday = (4, "Thursday")
    Friday = (5, "Friday")
    Saturday = (6, "Saturday")
    EveryDay = (7, "Every day")
    Weekdays = (8, "Weekdays")
    Weekends = (9, "Weekends")

class ActiveInputEnum(VictronEnum):
    AC_INPUT_1 = (0, "AC Input 1")
    AC_INPUT_2 = (1, "AC Input 2")
    DISCONNECTED = (240, "Disconnected")

class SolarChargerDeviceOffReason(VictronEnum):
    NONE = (0x00, "-")
    NoInputPower = (0x01, "No/Low input power")
    SwitchedOffPowerSwitch = (0x02, "Switched off (power switch)")
    SwitchedOffDeviceModeRegister = (0x04, "Switched off (device mode register)")
    RemoteInput = (0x08, "Remote input")
    ProtectiveAction = (0x10, "Protection active")
    NeedToken = (0x20, "Need token for operation")
    SignalFromBMS = (0x40, "Signal from BMS")
    EngineShutdow = (0x80, "Engine shutdown on low input voltage")
    AnalysingInputVoltage = (0x100, "Analysing input voltage")
    LowTemperature = (0x200, "Low temperature")
    NoPanelPower = (0x400, "No/Low panel power")
    NoBatteryPower = (0x800, "No/Low battery power")
    ActiveAlarm = (0x8000, "Active alarm")