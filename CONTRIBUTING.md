# Extending Victron MQTT Topic Map

This guide explains how to extend the `_victron_topics.py` and `_victron_enums.py` file to add support for additional Victron MQTT topics and devices.

## Overview

The `_victron_topics.py` file contains a dictionary that maps MQTT topic patterns to `TopicDescriptor` objects. Each descriptor defines how the topic should be interpreted, what type of entity it represents, and how its values should be processed.

## Understanding MQTT Topic Patterns

Victron Venus OS uses a structured MQTT topic hierarchy. The general pattern is:

```
N/{portal_id}/{service_type}/{device_instance}/{metric_path}
```

Where:
- `N` = Notification (always N for Victron)
- `{portal_id}` = Installation identifier (use `+` as wildcard)
- `{service_type}` = Type of service (battery, solarcharger, vebus, etc.)
- `{device_instance}` = Instance number of the device (use `+` as wildcard)
- `{metric_path}` = Path to the specific metric

### Common Topic Patterns

- Device attributes: `N/+/+/+/ProductName`, `N/+/+/+/Serial`
- Device metrics: `N/+/battery/+/Dc/0/Voltage`
- Phase-specific metrics: `N/+/grid/+/Ac/+/Power` (where last `+` is phase L1, L2, L3)
- System-level metrics: `N/+/system/+/Ac/Grid/NumberOfPhases`

## TopicDescriptor Structure

Each MQTT topic is mapped to a `TopicDescriptor` with the following properties:

### Required Properties

- **`message_type`**: Type of Home Assistant entity (`MetricKind` enum)
- **`short_id`**: Unique identifier for the metric
- **`metric_type`**: Physical type of measurement (`MetricType` enum)
- **`metric_nature`**: Nature of the metric (`MetricNature` enum)
- **`value_type`**: Data type of the value (`ValueType` enum)

### Optional Properties

- **`name`**: Human-readable name (required for non-attributes)
- **`unit_of_measurement`**: Physical unit (V, A, W, etc.)
- **`device_type`**: Type of device (`DeviceType` enum)
- **`precision`**: Number of decimal places
- **`enum`**: Enum class for enumerated values
- **`min`/`max`**: Value ranges for number inputs

## Available Enums and Constants

### MetricKind (Entity Types)
```python
ATTRIBUTE      # Device attributes (model, serial, etc.) - You will not need to use this one in most cases.
SENSOR         # Read-only measurements
BINARY_SENSOR  # On/off states
SWITCH         # Controllable on/off
SELECT         # Dropdown selection
NUMBER         # Numeric input control
```

### MetricType (Physical Measurements)
```python
POWER                       # Watts
ENERGY                      # kWh
VOLTAGE                     # Volts
CURRENT                     # Amperes
TEMPERATURE                 # Celsius
FREQUENCY                   # Hertz
PERCENTAGE                  # Percent
ELECTRIC_STORAGE_CAPACITY   # Amp-hours
```

### MetricNature (Measurement Characteristics)
```python
INSTANTANEOUS  # Current value
CUMULATIVE     # Ever-increasing counter
DELTA          # Change since last reading
NONE           # Not applicable
```

### ValueType (Data Types)
```python
INT            # Integer
INT_DEFAULT_0  # Integer defaulting to 0
FLOAT          # Floating point
STRING         # Text
ENUM           # Enumerated value
```

### DeviceType (Device Categories)
```python
SYSTEM         # System-wide metrics
SOLAR_CHARGER  # MPPT solar chargers
INVERTER       # Inverters/chargers
BATTERY        # Battery monitors
GRID           # Grid connection
EVCHARGER      # EV chargers
PVINVERTER     # PV inverters
```

## Adding New Topic Definitions

### Step 1: Identify the MQTT Topic Structure

First, determine the exact MQTT topic pattern. Use tools like [mqtt explorer](https://mqtt-explorer.com/) or the included `dump_mqtt.py` scripts to monitor MQTT traffic. I also recommend [mqtt explorer add-on](https://github.com/adamoutler/mqtt-explorer) if your boat is away and have internet connectivity.


### Step 2: Create the TopicDescriptor

Add a new entry to the `topic_map` dictionary:

```python
"N/+/service_type/+/MetricPath": TopicDescriptor(
    message_type=MetricKind.SENSOR,          # Entity type
    short_id="unique_metric_id",             # Unique identifier
    name="Human Readable Name",              # Display name
    unit_of_measurement="V",                 # Physical unit
    metric_type=MetricType.VOLTAGE,          # Measurement type
    metric_nature=MetricNature.INSTANTANEOUS, # Measurement nature
    device_type=DeviceType.BATTERY,          # Device category
    value_type=ValueType.FLOAT,              # Data type
    precision=1,                             # Decimal places
),
```

### Step 3: Handle Phase-Specific Metrics

For multi-phase systems, use the `{phase}` placeholder in `short_id` and `name`:

```python
"N/+/grid/+/Ac/+/Voltage": TopicDescriptor(
    message_type=MetricKind.SENSOR,
    short_id="grid_voltage_{phase}",         # Will become grid_voltage_L1, etc.
    name="Grid voltage on {phase}",          # Will become "Grid voltage on L1"
    unit_of_measurement="V",
    metric_type=MetricType.VOLTAGE,
    metric_nature=MetricNature.INSTANTANEOUS,
    device_type=DeviceType.GRID,
    value_type=ValueType.FLOAT,
    precision=1,
),
```

## Adding New Device Types

### Step 1: Add to DeviceType Enum

If you're adding support for a new device category, add it to the `DeviceType` enum in `constants.py`:

```python
class DeviceType(Enum):
    # ... existing types ...
    NEW_DEVICE = "new_device"
```

### Step 2: Add Device-Specific Topics

Add the device's MQTT topics to the topic map, using the new device type:

```python
"N/+/new_device/+/SomeMetric": TopicDescriptor(
    message_type=MetricKind.SENSOR,
    short_id="new_device_metric",
    name="New Device Metric",
    device_type=DeviceType.NEW_DEVICE,
    # ... other properties
),
```

## Adding Enumerated Values

### Step 1: Create Enum Class

For metrics with predefined values, create a new enum in `victron_enums.py`:

```python
class NewDeviceMode(VictronEnum):
    """New Device Mode Enum"""
    Mode1 = (0, "Mode 1")
    Mode2 = (1, "Mode 2")
    Mode3 = (2, "Mode 3")
```

### Step 2: Use in TopicDescriptor

Reference the enum in your topic descriptor:

```python
"N/+/new_device/+/Mode": TopicDescriptor(
    message_type=MetricKind.SELECT,
    short_id="new_device_mode",
    name="New Device Mode",
    metric_type=MetricType.NONE,
    metric_nature=MetricNature.NONE,
    device_type=DeviceType.NEW_DEVICE,
    value_type=ValueType.ENUM,
    enum=NewDeviceMode,
),
```

## Adding Controllable Entities

For metrics that can be controlled (switches, selects, numbers), use appropriate `MetricKind` values:

### Switch Example
```python
"N/+/device/+/EnableSomething": TopicDescriptor(
    message_type=MetricKind.SWITCH,
    short_id="device_enable",
    name="Enable Something",
    device_type=DeviceType.DEVICE,
    value_type=ValueType.ENUM,
    enum=GenericOnOff,
),
```

### Number Input Example
```python
"N/+/device/+/SetCurrent": TopicDescriptor(
    message_type=MetricKind.NUMBER,
    short_id="device_set_current",
    name="Set Current",
    unit_of_measurement="A",
    metric_type=MetricType.CURRENT,
    device_type=DeviceType.DEVICE,
    value_type=ValueType.INT,
    precision=0,
    min=0,
    max=32,
),
```

## Common Patterns and Examples

### Battery Management System Metrics
```python
"N/+/battery/+/System/MinCellVoltage": TopicDescriptor(
    message_type=MetricKind.SENSOR,
    short_id="battery_min_cell_voltage",
    name="Battery minimum cell voltage",
    unit_of_measurement="V",
    metric_type=MetricType.VOLTAGE,
    metric_nature=MetricNature.INSTANTANEOUS,
    device_type=DeviceType.BATTERY,
    value_type=ValueType.FLOAT,
    precision=3,
),
```

### Tank Level Sensors
```python
"N/+/tank/+/Level": TopicDescriptor(
    message_type=MetricKind.SENSOR,
    short_id="tank_level",
    name="Tank level",
    unit_of_measurement="%",
    metric_type=MetricType.PERCENTAGE,
    metric_nature=MetricNature.INSTANTANEOUS,
    device_type=DeviceType.TANK,  # You'd need to add this to DeviceType
    value_type=ValueType.FLOAT,
    precision=1,
),
```

### Temperature Sensors
```python
"N/+/temperature/+/Temperature": TopicDescriptor(
    message_type=MetricKind.SENSOR,
    short_id="temperature_sensor",
    name="Temperature",
    unit_of_measurement="°C",
    metric_type=MetricType.TEMPERATURE,
    metric_nature=MetricNature.INSTANTANEOUS,
    device_type=DeviceType.TEMPERATURE,  # You'd need to add this to DeviceType
    value_type=ValueType.FLOAT,
    precision=1,
),
```

## Testing Your Changes

1. **Validate topic patterns**: Ensure your MQTT topic patterns match actual Venus OS output
2. **Test with real data**: Use the included `view_metric.py` scripts to verify your mappings work
   ```bash
   cd src
   python -m victron_mqtt.utils.view_metrics
   ```
3. **Check for conflicts**: Ensure your `short_id` values are unique
4. **Run tests**: Execute the test suite to verify no regressions. This requires you to specify connection parameters (see `conftest.py`)

```bash
# Run the test suite
hatch test
```

## Best Practices

1. **Use descriptive short_ids**: Make them unique and self-explanatory
2. **Follow naming conventions**: Use snake_case for IDs, proper capitalization for names
3. **Set appropriate precision**: Don't over-specify decimal places
4. **Group related metrics**: Keep similar device types together in the file
5. **Add comments**: Document special cases or unusual topic patterns
6. **Validate units**: Ensure unit_of_measurement matches the actual data
7. **Consider device variations**: Some devices may have slightly different topic structures

## Common Pitfalls

- **Wildcards in wrong positions**: Ensure `+` wildcards match the actual topic structure
- **Missing precision for floats**: Always specify appropriate precision for numeric values
- **Wrong MetricNature**: Energy counters should be CUMULATIVE, instantaneous readings should be INSTANTANEOUS
- **Conflicting short_ids**: Each metric must have a unique short_id within its device
- **Missing device_type**: Always specify the appropriate device type for proper grouping

## Getting Help

- Check existing patterns in `_victron_topics.py` for similar metrics
- Monitor MQTT traffic to understand the exact topic structure
- Review Venus OS documentation for metric meanings
- Test with real hardware when possible
