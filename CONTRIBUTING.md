# Victron MQTT Contribution Guide

Thank you for helping extend the library! This guide explains how to add new MQTT topics, enums, and device types.

## Finding MQTT Topics

To add new metrics, you first need to discover the MQTT topics published by your Victron system.

### Using MQTT Explorer

1. Download [MQTT Explorer](https://mqtt-explorer.com/) (Windows, macOS, Linux)
2. Connect to your Venus OS device (usually `venus.local:1883`)
3. Expand the `N` node to see all topics
4. Click on topics to see their values and history

**Tip:** Change a value on your Victron dashboard (e.g., turn a load on/off) and watch for updates in MQTT Explorer to identify which topic corresponds to which value.

### Using the Built-in Dump Tool

```bash
python -m victron_mqtt.utils.dump_mqtt --host venus.local. --port 1883
```

### Reference Documentation

- [Venus OS D-Bus wiki](https://github.com/victronenergy/venus/wiki/dbus) — detailed topic documentation and possible values
- [Modbus TCP Register List](https://view.officeapps.live.com/op/view.aspx?src=https%3A%2F%2Fwww.victronenergy.com%2Fupload%2Fdocuments%2FCCGX-Modbus-TCP-register-list-3.60.xlsx) — the `dbus-obj-path` column maps to MQTT topics

---

## MQTT Topic Structure

Victron Venus OS uses a structured MQTT topic hierarchy:

```
N/{installation_id}/{service_type}/{device_id}/{metric_path}
```

- `N` — notification prefix (always `N`)
- `{installation_id}` — installation identifier (auto-discovered)
- `{service_type}` — device type (`battery`, `solarcharger`, `grid`, etc.)
- `{device_id}` — instance number of the device
- `{metric_path}` — path to the specific metric

## File Structure

| File | Purpose |
|---|---|
| `victron_mqtt/_victron_topics.py` | All topic descriptors (the main file you'll edit) |
| `victron_mqtt/_victron_enums.py` | Enum definitions for enumerated values |
| `victron_mqtt/__init__.py` | Public API exports |

---

## Adding New Topics

### Step 1: Create the TopicDescriptor

Add a new entry to the `topics` list in `_victron_topics.py`. **Topics are sorted alphabetically by their `topic` field** — insert your new entry in the correct position.

```python
TopicDescriptor(
    topic="N/{installation_id}/battery/{device_id}/System/MinCellVoltage",
    message_type=MetricKind.SENSOR,
    short_id="battery_min_cell_voltage",
    name="Battery minimum cell voltage",
    metric_type=MetricType.VOLTAGE,
    # unit_of_measurement, value_type, precision auto-set by MetricType defaults
),
```

### TopicDescriptor Fields

#### Required

| Field | Description |
|---|---|
| `topic` | MQTT topic pattern with `{installation_id}` and `{device_id}` placeholders |
| `message_type` | Entity kind: `SENSOR`, `BINARY_SENSOR`, `SWITCH`, `SELECT`, `NUMBER`, `TIME`, `BUTTON`, `ATTRIBUTE`, `DEVICE_TRACKER` |
| `short_id` | Unique identifier for the metric (snake_case, lowercase) |
| `name` | Human-readable display name (required for non-ATTRIBUTEs, start with capital letter) |

#### Optional

| Field | Description | Default |
|---|---|---|
| `value_type` | `INT`, `FLOAT`, `STRING`, `ENUM`, `BITMASK`, `EPOCH` | Auto-set by metric_type |
| `metric_type` | `VOLTAGE`, `POWER`, `ENERGY`, `CURRENT`, `TEMPERATURE`, `FREQUENCY`, `PERCENTAGE`, etc. | `NONE` |
| `metric_nature` | `MEASUREMENT`, `TOTAL`, `TOTAL_INCREASING` | Auto-set by metric_type |
| `unit_of_measurement` | Physical unit (`V`, `A`, `W`, `kWh`, `°C`, etc.) | Auto-set by metric_type |
| `precision` | Decimal places for float values | Auto-set by metric_type |
| `enum` | Enum class for `ENUM`/`BITMASK` value types | `None` |
| `min` / `max` | Value range for `NUMBER` inputs | `None` |
| `step` | Step size for `NUMBER` inputs | `None` |
| `main_topic` | `True` if this is the main entity for the device | `False` |
| `experimental` | `True` to only include in `EXPERIMENTAL` operation mode | `False` |
| `hidden` | `True` to hide from public APIs (used by formula source metrics) | `False` |
| `sub_device_key` | Placeholder name that creates sub-devices (e.g., `"output"`) | `None` |
| `depends_on` | List of metric short_ids this formula depends on | `[]` |

#### MetricType Defaults

Many fields auto-populate based on `metric_type`. For example, setting `metric_type=MetricType.VOLTAGE` automatically sets:
- `unit_of_measurement = "V"`
- `value_type = ValueType.FLOAT`
- `precision = 3`
- `metric_nature = MetricNature.MEASUREMENT`

So you often only need to specify `metric_type` and the rest fills in.

### Step 2: Handle Phase-Specific Metrics

For multi-phase metrics (L1/L2/L3), use `+` in the topic and `{phase}` in `short_id` and `name`:

```python
TopicDescriptor(
    topic="N/{installation_id}/grid/{device_id}/Ac/+/Voltage",
    message_type=MetricKind.SENSOR,
    short_id="grid_voltage_{phase}",
    name="Grid voltage on {phase}",
    metric_type=MetricType.VOLTAGE,
),
```

### Step 3: Handle Range Placeholders

For topics with numbered variants, use the `{name(start-end)}` syntax:

```python
TopicDescriptor(
    topic="N/{installation_id}/battery/{device_id}/Voltages/Cell{cell_id(1-16)}",
    message_type=MetricKind.SENSOR,
    short_id="battery_cell_{cell_id}_voltage",
    name="Cell {cell_id} voltage",
    metric_type=MetricType.VOLTAGE,
),
```

This auto-expands into 16 separate topic subscriptions, one per cell.

---

## Adding New Enums

### Step 1: Create the Enum Class

Add to `_victron_enums.py`. Each member takes three arguments: `(code, id, string)`:

```python
class NewDeviceMode(VictronEnum):
    """New Device Mode Enum"""

    MODE_A = (0, "mode_a", "Mode A")
    MODE_B = (1, "mode_b", "Mode B")
    MODE_C = (2, "mode_c", "Mode C")
```

- `code` — the numeric value from MQTT
- `id` — snake_case identifier (used for HA entity state)
- `string` — human-readable display name

### Step 2: Use in TopicDescriptor

```python
TopicDescriptor(
    topic="N/{installation_id}/device/{device_id}/Mode",
    message_type=MetricKind.SELECT,
    short_id="device_mode",
    name="Device mode",
    value_type=ValueType.ENUM,
    enum=NewDeviceMode,
),
```

### Step 3: Export in `__init__.py`

Add the import and `__all__` entry:

```python
from ._victron_enums import ..., NewDeviceMode

__all__ = [
    ...,
    "NewDeviceMode",
]
```

---

## Adding New Device Types

If you're adding topics for a device type that doesn't exist yet:

### Step 1: Add to DeviceType Enum

In `_victron_enums.py`:

```python
class DeviceType(VictronDeviceEnum):
    # ...existing entries...
    NEW_DEVICE = ("newdevice", "new_device", "New Device")
```

Arguments: `(mqtt_code, enum_id, display_string)`

- `mqtt_code` — must exactly match the device type in the MQTT topic path
- `enum_id` — snake_case identifier
- `display_string` — human-readable name

### Step 2: Add Device Topics

Add topics to `_victron_topics.py` in alphabetical order.

---

## Adding Controllable Entities

### Switch (on/off)

```python
TopicDescriptor(
    topic="N/{installation_id}/device/{device_id}/Enable",
    message_type=MetricKind.SWITCH,
    short_id="device_enable",
    name="Enable",
    value_type=ValueType.ENUM,
    enum=GenericOnOff,
),
```

Switches must use an enum with exactly two members: `id="on"` and `id="off"`.

### Number Input

```python
TopicDescriptor(
    topic="N/{installation_id}/device/{device_id}/SetCurrent",
    message_type=MetricKind.NUMBER,
    short_id="device_set_current",
    name="Set current",
    metric_type=MetricType.CURRENT,
    min=0,
    max=32,
),
```

### Select (dropdown)

```python
TopicDescriptor(
    topic="N/{installation_id}/device/{device_id}/Mode",
    message_type=MetricKind.SELECT,
    short_id="device_mode",
    name="Mode",
    value_type=ValueType.ENUM,
    enum=NewDeviceMode,
),
```

---

## Sub-Device Topics

Some devices contain sub-devices (e.g., switch SwitchableOutputs). Use `sub_device_key` to create separate child devices:

```python
# Attribute on the sub-device (sets device name)
TopicDescriptor(
    topic="N/{installation_id}/switch/{device_id}/SwitchableOutput/{output}/Settings/CustomName",
    message_type=MetricKind.ATTRIBUTE,
    short_id="custom_name",
    value_type=ValueType.STRING,
    sub_device_key="output",
),
# Metric on the sub-device
TopicDescriptor(
    topic="N/{installation_id}/switch/{device_id}/SwitchableOutput/{output}/State",
    message_type=MetricKind.SWITCH,
    short_id="switch_{output}_state",
    name="State",
    value_type=ValueType.ENUM,
    enum=GenericOnOff,
    sub_device_key="output",
),
```

Each unique `{output}` value creates a separate sub-device with `parent_device` pointing to the parent switch.

---

## Testing

### Run the Test Suite

```bash
# Static validation tests (no MQTT connection required)
python -m pytest tests/static_test.py tests/static_hub_test.py tests/parsed_topics_test.py

# All tests
python -m pytest tests/
```

### What the Static Tests Check

- No duplicate `short_id` values
- No duplicate device type + name combinations
- Required fields present for sensors
- Names start with capital letters
- Enum consistency (SWITCH topics must have on/off enum)
- Topics sorted alphabetically
- Valid device types in topic paths
- No forbidden placeholders in short_id or name

### Manual Testing

Use the metric viewer to verify your changes work with real data:

```bash
python -m victron_mqtt.utils.view_metrics
```

---

## Best Practices

1. **Keep topics alphabetically sorted** in `_victron_topics.py`
2. **Use descriptive short_ids** — unique, snake_case, self-explanatory
3. **Let MetricType set defaults** — don't manually set unit/precision/nature when MetricType handles it
4. **Follow naming conventions** — sentence case for names, snake_case for short_ids
5. **Add enums to `__init__.py`** — all `VictronEnum` subclasses must be exported
6. **Test with real hardware** when possible — verify topic patterns match actual MQTT output
7. **Attach `dump_mqtt` output** to your PR for review

## Common Pitfalls

- **Wrong sort order** — the alphabetical sort test will fail if topics aren't in order
- **Missing enum export** — new enums must be added to `__init__.py`'s `__all__`
- **Wrong MetricNature** — energy counters should be `TOTAL`, instantaneous readings should be `MEASUREMENT`
- **Precision on non-float types** — `STRING`, `ENUM`, `BITMASK` must not have precision set
- **Phase placeholder** — topics with `+` for L1/L2/L3 must use `{phase}` in short_id and name

## Getting Help

- Check existing patterns in `_victron_topics.py` for similar metrics
- Review the [Venus OS D-Bus wiki](https://github.com/victronenergy/venus/wiki/dbus)
- Open an [issue](https://github.com/tomer-w/victron_mqtt/issues) if you need guidance
