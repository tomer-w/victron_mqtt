# 🌟 Supercharge Your Victron Devices with victron_mqtt!

[![PyPI - Version](https://img.shields.io/pypi/v/victron_mqtt.svg)](https://pypi.org/project/victron_mqtt)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/victron_mqtt.svg)](https://pypi.org/project/victron_mqtt)

-----

## 🚀 Welcome to victron_mqtt!

Are you ready to unlock the full potential of your Victron devices? `victron_mqtt` is here to make your Venus OS experience smoother, faster, and way more fun! Whether you're a seasoned developer or just starting your journey, this library is your gateway to seamless communication with Victron's Venus OS devices like the CCGX, Cerbo GX, and Ekrano GX.
This package is the backend for the Home Assistant [Victron Venus MQTT](https://github.com/tomer-w/ha-victron-mqtt) custom integration.


If you just want to browse the Victron MQTT definitions, please go to the [documentation page](https://tomer-w.github.io/victron_mqtt/).  
You can consume the Victron MQTT definitions [here](https://raw.githubusercontent.com/tomer-w/victron_mqtt/refs/heads/main/victron_mqtt.json).

> **Disclaimer:** This is a third-party library and is not affiliated with Victron Energy.

## 🌟 Features

- **⚡ Asynchronous Communication:** Built for modern Python applications, ensuring non-blocking operations.
- **🔍 Device Metrics Viewer:** A Tk-based viewer application to inspect metrics and devices.
- **🛠️ Utility Tools:** Includes utilities like `dump_mqtt` for exploring the MQTT structure.
- **📈 Extensibility:** Easily extendable to support additional metrics and configurations.

## 📦 Installation

Getting started is as easy as pie! Just run:

```bash
pip install victron_mqtt
```

## 🧑‍💻 Usage

### 🎨 Viewer Application

Want to see your Victron devices in action? Fire up the viewer application written in Tk:

```bash
python3 -m victron_mqtt.utils.view_metrics
```

This viewer is not just functional—it's a great example of how to use the library in your own projects.

### 🕵️‍♂️ Dump MQTT Structure

Curious about the full MQTT structure from your device? Dive deep with the `dump_mqtt` utility:

```bash
# Dumps a full MQTT structure into fullvictrondump.txt
python3 -m victron_mqtt.utils.dump_mqtt > fullvictrondump.txt

# Command-line help for specifying connection details:
python3 -m victron_mqtt.utils.dump_mqtt --help
```

## Help Needed!!
Please help with extending the library with more topics. See instructions [here](extending-victron-support.md) for how to contribute.

## ⚠️ Limitations and Known Issues

- **🧪 Limited Testing:** The library has been tested with a single configuration of a Victron installation. It may not include all metrics relevant to other setups.
- **🔒 Read-Only:** Currently, the library supports data retrieval only. Changing settings is not yet implemented.

## 🐞 Logging Issues

Found a bug or need help? We're here for you! Log issues on [GitHub](https://github.com/tomer-w/victron_mqtt/issues).

To help us support your setup, you can attach the output of the `dump_mqtt` utility to your issue.

## 📜 License

`victron_mqtt` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.

## Acknowledgments

- Thanks to Johan du Plessis <johan@epicwin.co.za> who [started](https://github.com/JohansLab/victronvenusclient) the original library this one is based on. It is not clear if the original library is still maintained, so I forked it and continue to make progress with it.
- Thanks to Victron Energy for their excellent hardware and documentation
