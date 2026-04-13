# victron_mqtt

[![PyPI - Version](https://img.shields.io/pypi/v/victron_mqtt.svg)](https://pypi.org/project/victron_mqtt)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/victron_mqtt.svg)](https://pypi.org/project/victron_mqtt)

An asynchronous Python library for communicating with Victron Energy Venus OS devices (CCGX, Cerbo GX, Ekrano GX) via MQTT. It maps Victron MQTT topics to typed Python objects with live-updating metrics, writable controls, and device hierarchy support.

This package is the backend for the Home Assistant [Victron GX](https://github.com/tomer-w/ha-victron-mqtt) integration.

> **Disclaimer:** This is a third-party library and is not affiliated with Victron Energy.

## Features

- **Asynchronous** — non-blocking MQTT communication built on `paho-mqtt`
- **Typed device & metric model** — devices, metrics, enums, and values are fully typed Python objects
- **Live updates** — metrics update in real-time via callbacks as MQTT messages arrive
- **Writable metrics** — control switches, numbers, selects, and time values on your Victron system
- **Device hierarchy** — parent/child device relationships (e.g., switch → SwitchableOutput sub-devices)
- **Formula metrics** — computed metrics derived from other metrics (e.g., GPS location, energy calculations)
- **Hidden metrics** — source metrics consumed by formulas are hidden from public APIs
- **Device tracker** — combined GPS location with latitude, longitude, altitude, course, speed, and fix handling
- **Metric viewer** — built-in tkinter GUI for browsing devices and metrics with live updates

## Installation

```bash
pip install victron_mqtt
```

## Quick Start

```python
import asyncio
import victron_mqtt

async def main():
    # Connect to your Venus OS device
    hub = victron_mqtt.Hub("venus.local.", 1883, None, None, False)
    await hub.connect()
    await hub.wait_for_first_refresh()

    # Browse devices and metrics
    for device in hub.devices.values():
        print(f"Device: {device.name} ({device.device_type})")
        for metric in device.metrics:
            print(f"  {metric.short_id}: {metric.formatted_value}")

    await hub.disconnect()

asyncio.run(main())
```

## Core Concepts

### Hub

The `Hub` is the main entry point. It manages the MQTT connection, discovers devices, and routes metric updates.

```python
hub = victron_mqtt.Hub(
    host="venus.local.",       # MQTT broker hostname or IP
    port=1883,                 # MQTT broker port
    username=None,             # Optional MQTT username
    password=None,             # Optional MQTT password
    use_ssl=False,             # Enable SSL/TLS
    installation_id=None,      # Auto-discovered if not provided
    operation_mode=OperationMode.FULL,  # FULL, READ_ONLY, or EXPERIMENTAL
    device_type_exclude_filter=None,    # Exclude specific device types
    update_frequency_seconds=None,      # Throttle update frequency
)
```

**Key properties:**
- `hub.devices` — dict of all devices with visible metrics
- `hub.installation_id` — the Venus OS installation identifier
- `hub.connected` — whether the MQTT connection is active
- `hub.get_metric(unique_id)` — look up a metric by its unique ID

### Devices

Each Victron service (solar charger, battery, inverter, etc.) becomes a `Device` with properties like name, model, manufacturer, and serial number.

```python
device = hub.devices["solarcharger_288"]
print(device.name)            # "SmartSolar MPPT 150|35"
print(device.device_type)     # DeviceType.SOLAR_CHARGER
print(device.model)           # "SmartSolar MPPT 150|35"
print(device.parent_device)   # parent Device or None
```

**Device hierarchy:** Sub-devices (like SwitchableOutput channels) have a `parent_device` reference pointing to their parent. Top-level devices are parented to the system device (`system_0`).

### Metrics

Metrics represent individual data points on a device. Each metric has a kind, type, value, and optional unit.

```python
metric = device.get_metric("solarcharger_yield_today")
print(metric.name)              # "Yield today"
print(metric.value)             # 3.45
print(metric.formatted_value)   # "3.45 kWh"
print(metric.metric_kind)       # MetricKind.SENSOR
print(metric.metric_type)       # MetricType.ENERGY
print(metric.unit_of_measurement)  # "kWh"
```

**Metric kinds:** `SENSOR`, `BINARY_SENSOR`, `SWITCH`, `SELECT`, `NUMBER`, `TIME`, `BUTTON`, `DEVICE_TRACKER`

### Writable Metrics

Switches, numbers, selects, and time metrics can be written back to the device:

```python
from victron_mqtt import WritableMetric

metric = device.get_metric("evcharger_charge")
if isinstance(metric, WritableMetric):
    metric.set("on")   # Turn on
    metric.set("off")  # Turn off

# Number metrics accept float values
metric = device.get_metric("system_ac_power_setpoint")
if isinstance(metric, WritableMetric):
    metric.set(500.0)  # Set to 500W

# Select metrics accept enum id strings
metric = device.get_metric("system_ess_mode")
if isinstance(metric, WritableMetric):
    metric.set("optimized")
```

### Callbacks

Register callbacks to be notified when new devices or metrics are discovered:

```python
def on_new_device(hub, device):
    print(f"New device: {device.name} (parent: {device.parent_device})")

def on_new_metric(hub, device, metric):
    print(f"New metric on {device.name}: {metric.name} = {metric.formatted_value}")

hub.on_new_device = on_new_device  # Fires for each new device
hub.on_new_metric = on_new_metric  # Fires for each new visible metric
```

**Notification order:** Devices are notified in topological order — parent devices always before their children. System devices are prioritized at the same depth.

Subscribe to live metric updates:

```python
metric = device.get_metric("grid_power")
metric.on_update = lambda metric, value: print(f"Grid power: {value}W")
```

### GPS Location

GPS data is combined into a single `GpsLocation` object with `DEVICE_TRACKER` metric kind:

```python
from victron_mqtt import GpsLocation

metric = device.get_metric("gps_location")
if isinstance(metric.value, GpsLocation):
    print(f"Lat: {metric.value.latitude}")
    print(f"Lon: {metric.value.longitude}")
    print(f"Alt: {metric.value.altitude}")
    print(f"Course: {metric.value.course}")
    print(f"Speed: {metric.value.speed}")
```

The GPS formula returns `None` when the GPS has no fix (`Fix=0`), so consumers can handle the "no position" state gracefully.

### Enums

Victron enums provide code, id, and human-readable string representations:

```python
from victron_mqtt import BatteryState

state = BatteryState.from_code(5)
print(state.code)    # 5
print(state.id)      # "float"
print(state.string)  # "Float"
print(state)         # "Float"
```

### Operation Modes

- `OperationMode.FULL` — all metrics, writable controls enabled
- `OperationMode.READ_ONLY` — all writable metrics become read-only sensors
- `OperationMode.EXPERIMENTAL` — includes experimental/unstable metrics

### Device Type Filtering

Exclude specific device types from discovery:

```python
from victron_mqtt import DeviceType

hub = victron_mqtt.Hub(
    "venus.local.", 1883, None, None, False,
    device_type_exclude_filter=[DeviceType.TEMPERATURE, DeviceType.GPS],
)
```

## Supported Device Types

| Device Type | Code | Description |
|---|---|---|
| `SYSTEM` | `system` | Venus OS system |
| `SOLAR_CHARGER` | `solarcharger` | MPPT solar chargers |
| `INVERTER` | `inverter` | VE.Direct inverters |
| `BATTERY` | `battery` | Battery monitors |
| `GRID` | `grid` | Grid meters |
| `VEBUS` | `vebus` | Multi/Quattro inverter-chargers |
| `EVCHARGER` | `evcharger` | EV charging stations |
| `PVINVERTER` | `pvinverter` | PV inverters |
| `TEMPERATURE` | `temperature` | Temperature sensors |
| `GENERATOR` | `generator` | Generator start/stop |
| `TANK` | `tank` | Liquid tank sensors |
| `GPS` | `gps` | GPS receivers |
| `SWITCH` | `switch` | Switches and SwitchableOutputs |
| `DIGITAL_INPUT` | `digitalinput` | Digital inputs |
| `DC_SYSTEM` | `dcsystem` | DC system |
| `DC_LOAD` | `dcload` | DC loads |
| `ALTERNATOR` | `alternator` | Alternator chargers |
| `CHARGER` | `charger` | AC chargers |
| `HEATPUMP` | `heatpump` | Heat pumps |
| `ACLOAD` | `acload` | AC loads |
| `DCDC` | `dcdc` | DC/DC chargers |
| `TRANSFER_SWITCH` | `TransferSwitch` | Transfer switches |

## Tools

### Metric Viewer

Interactive GUI for browsing devices and metrics with live updates:

```bash
python -m victron_mqtt.utils.view_metrics
```

Features: hierarchical device tree, search/filter, color-coded metric kinds, double-click to view/edit, live value updates, status bar.

### MQTT Dump

Dump the raw MQTT structure from your device:

```bash
python -m victron_mqtt.utils.dump_mqtt --host venus.local. --port 1883
```

### Topic Definitions

Browse all supported MQTT topic definitions on the [documentation page](https://tomer-w.github.io/victron_mqtt/).

The machine-readable topic definitions JSON is available [here](https://raw.githubusercontent.com/tomer-w/victron_mqtt/refs/heads/main/victron_mqtt.json).

## Contributing

Help extend the library with more topics! See [CONTRIBUTING.md](CONTRIBUTING.md) for instructions.

## Logging Issues

Found a bug? Log issues on [GitHub](https://github.com/tomer-w/victron_mqtt/issues).

Attach the output of `dump_mqtt` to help us debug your setup.

## License

`victron_mqtt` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.

## Acknowledgments

- Thanks to Johan du Plessis <johan@epicwin.co.za> who [started](https://github.com/JohansLab/victronvenusclient) the original library this one is based on.
- Thanks to Victron Energy for their excellent hardware and documentation.
