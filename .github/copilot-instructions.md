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

## GitHub Issue Analysis

When processing a GitHub issue:

1. Look for MQTT topic strings (usually from MQTT Explorer output)
2. Identify the enum values and their numeric codes
3. Extract the device type from the topic path
4. Create descriptive names for short_id and name fields
5. Choose appropriate message_type and value_type

## Example Issue Processing

For battery alarm topics from issue #35:
- Topic: `N/c0619ab48793/battery/512/Alarms/HighChargeCurrent`
- Values: 0=No alarm, 1=Almost discharged, 2=Alarm
- Result: BatteryAlarmEnum + 7 topic descriptors for different alarm types

## Testing

Ensure changes pass static tests:
- No duplicate short_ids
- Required fields present for sensors
- Enums properly exported in __init__.py
- Valid topic structure