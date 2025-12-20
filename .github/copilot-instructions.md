# GitHub Copilot Instructions: Adding New Topics from Issues

This file provides instructions for GitHub Copilot on how to add new MQTT topics and enums to the victron_mqtt project based on GitHub issues.

## Context
The victron_mqtt project maps Victron Energy MQTT topics to Python objects. Users submit GitHub issues requesting new topics (usually for specific devices or features they want to monitor).

## File Structure
- `victron_mqtt/_victron_enums.py` - Contains all enum definitions
- `victron_mqtt/_victron_topics.py` - Contains all topic descriptors  
- `victron_mqtt/__init__.py` - Public API exports

## Adding New Enums

When a GitHub issue requests topics that need new enum values:

1. Add the enum class to `victron_mqtt/_victron_enums.py`:
```python
class BatteryAlarmEnum(VictronEnum):
    NoAlarm = (0, "No Alarm")
    Warning = (1, "Almost discharged") 
    Alarm = (2, "Alarm")
```

2. Import the enum in `victron_mqtt/_victron_topics.py`:
```python
from ._victron_enums import ..., BatteryAlarmEnum
```

3. Export the enum in `victron_mqtt/__init__.py`:
- Add to import: `from ._victron_enums import ..., BatteryAlarmEnum`
- Add to `__all__` list: `"BatteryAlarmEnum",`

## Adding New Device Types

If this is the first time adding topics for a new device type (e.g., `dcsystem`, `dcdc`, etc.):

1. **Add the device type to the DeviceType enum** in `victron_mqtt/_victron_enums.py`:
```python
class DeviceType(VictronDeviceEnum):
    # ...existing entries...
    DC_SYSTEM = ("dcsystem", "DC System")
```

### Notes
1. No need to add SETTINGS to the DeviceType Enum as it is handled differently.

2. **Follow the naming convention**:
   - First parameter: lowercase string matching the MQTT topic device type
   - Second parameter: human-readable display name
   - Use underscores in enum name, lowercase in MQTT topic

**Important**: The first parameter must exactly match the device type used in MQTT topics. For example, if topics use `N/{installation_id}/dcsystem/{device_id}/...`, then use `("dcsystem", "DC System")`.

## Adding New Topics

Add topic descriptors to the `topics` list in `victron_mqtt/_victron_topics.py`:

```python
TopicDescriptor(
    topic="N/{installation_id}/battery/{device_id}/Alarms/HighChargeCurrent",
    message_type=MetricKind.SENSOR,
    short_id="battery_high_charge_current",
    name="Battery high charge current",
    value_type=ValueType.ENUM,
    enum=BatteryAlarmEnum,
),
```

## Topic Pattern Guidelines

- Use `N/{installation_id}/{device_type}/{device_id}/...` format
- `short_id` must be unique across all topics
- `name` should be human-readable description
- For alarms/status: use `MetricKind.SENSOR` with `ValueType.ENUM`
- For measurements: use appropriate `MetricType` (VOLTAGE, CURRENT, POWER, etc.)
- When adding TopicDescriptor make sure to keep the alphabetical order which the file has based on the topic field.

## GitHub Issue Analysis

When processing a GitHub issue:

1. Look for MQTT topic strings (usually from MQTT Explorer output)
2. Identify the enum values and their numeric codes
3. Extract the device type from the topic path
4. **Check if the device type exists** in the DeviceType enum - if not, add it first
5. Create descriptive names for short_id and name fields
6. Choose appropriate message_type and value_type

## Example Issue Processing

For DC system topics from issue #111:
- Topics: `N/{installation_id}/dcsystem/{device_id}/Dc/0/Voltage`, etc.
- Device type: `dcsystem` (new - needed to add DC_SYSTEM to DeviceType enum)
- Values: Numeric measurements for voltage, current, power
- Result: DC_SYSTEM enum entry + 4 topic descriptors for DC measurements

For battery alarm topics from issue #35:
- Topic: `N/c0619ab48793/battery/512/Alarms/HighChargeCurrent`
- Values: 0=No alarm, 1=Almost discharged, 2=Alarm
- Device type: `battery` (already existed)
- Result: BatteryAlarmEnum + 7 topic descriptors for different alarm types

## Testing

Ensure changes pass static tests:
- No duplicate short_ids
- Required fields present for sensors
- Enums properly exported in __init__.py
- Valid topic structure