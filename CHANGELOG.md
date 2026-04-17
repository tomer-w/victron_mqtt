# Changelog

## 2026.4.17 (2026-04-17)

### Changes

- Fix casing

### Contributors

@github-actions[bot] and @tomer-w



## 2026.4.16 (2026-04-16)

### Changes

- Remove empty devices from the device chain: https://github.com/tomer-w/ha-victron-mqtt/issues/350

### Contributors

@github-actions[bot] and @tomer-w



## 2026.4.15 (2026-04-16)

### Changes

- Fix publish workflow

### Contributors

@tomer-w



## 2026.4.14 (2026-04-16)

### Changes

- Auto bump versions

### Contributors

@tomer-w



## 2026.4.13.2 (2026-04-16)

### Changes

- Add EV charger autostart metric: https://github.com/tomer-w/ha-victron-mqtt/issues/358

### Contributors

@tomer-w



## 2026.4.12 (2026-04-16)

### Changes

- Fix GPS with partial attributes: https://github.com/tomer-w/ha-victron-mqtt/issues/354

### Contributors

@tomer-w



## 2026.4.11 (2026-04-15)

### Changes

- Add better step values based on: https://github.com/tomer-w/ha-victron-mqtt/discussions/356
- move the viewer to split screen between the devices and metrics

### Contributors

@tomer-w



## 2026.4.10 (2026-04-15)

### Changes

- Fix regression with sub devices only working with numerical sub device ID: https://github.com/tomer-w/ha-victron-mqtt/issues/350

### Contributors

@tomer-w



## 2026.4.9 (2026-04-14)

### Changes

- Add more device classes

### Contributors

@tomer-w



## 2026.4.8 (2026-04-14)

### Changes

- Remove un-needed measurements based on: https://github.com/tomer-w/ha-victron-mqtt/issues/347

### Contributors

@tomer-w



## 2026.4.7 (2026-04-13)

### Changes

- Skip devices with no visible metrics and no children from notifications

### Contributors

@tomer-w



## 2026.4.6 (2026-04-13)

### Changes

- Get back phases units where appropriate
- Modernize view_metrics tool UX
- Add on_new_device callback and topological device notification ordering
- Merge feature/parent-device: SwitchableOutput sub-devices for switch and system
- Add more capabilities to the GPS metric
- prepare strings.json to final state

### Contributors

@tomer-w



## 2026.4.5 (2026-04-11)

### Changes

- Support all outputs of IP43 Charger. https://github.com/tomer-w/ha-victron-mqtt/issues/337
- dont translate hidden topics
- Remove phases as units
- Add Multi RS Solar DC temperature metric: https://github.com/tomer-w/victron_mqtt/issues/88

### ≡ƒº░ Maintenance

- Bump peter-evans/create-pull-request from 7 to 8 @[dependabot[bot]](https://github.com/apps/dependabot) (#89)
- Bump actions/github-script from 8 to 9 @[dependabot[bot]](https://github.com/apps/dependabot) (#90)
- Bump actions/checkout from 4 to 6 @[dependabot[bot]](https://github.com/apps/dependabot) (#91)
- Bump actions/setup-python from 5 to 6 @[dependabot[bot]](https://github.com/apps/dependabot) (#92)

### Contributors

@tomer-w


## 2026.4.4 (2026-04-11)

### Changes

- Add device tracker support for GPS device
- Add support for writing dump_victron output to file
- text fixes

### Contributors

@tomer-w



## 2026.4.3 (2026-04-09)

### Changes

- Add RESTART metric_type for button
- Lot of small text fixes
- Add tool to create HA core PRs when version is released.

### Contributors

@tomer-w



## 2026.4.2 (2026-04-07)

### Changes

- Add main_topic support

### Contributors

@tomer-w



## 2026.4.1 (2026-04-06)

### Changes

- Adding more MetricType values

### ≡ƒº░ Maintenance

- Bump actions/upload-artifact from 4 to 7 @[dependabot[bot]](https://github.com/apps/dependabot) (#87)
- Add HA core update workflow

### Contributors

@tomer-w and [dependabot[bot]](https://github.com/apps/dependabot)



## 2026.4.0 (2026-04-01)

### Changes

- remove dcdc none-existed topic
- centralize device name logic in the library

### Contributors

@tomer-w



## 2026.3.13 (2026-03-30)

### Changes

- Orion XS 1400 Battery Output Mode: https://github.com/tomer-w/victron_mqtt/issues/86
- Add battery voltage per inverter readings: https://github.com/tomer-w/ha-victron-mqtt/issues/329

### Contributors

@tomer-w



## 2026.3.12 (2026-03-28)

### Changes

- Fix couple of metric_natures

### Contributors

@tomer-w



## 2026.3.11 (2026-03-27)

### Changes

- Align MetricNature with HA ones

### ≡ƒº░ Maintenance

- Bump actions/deploy-pages from 4 to 5 @[dependabot[bot]](https://github.com/apps/dependabot) (#84)
- Bump actions/configure-pages from 5 to 6 @[dependabot[bot]](https://github.com/apps/dependabot) (#85)

### Contributors

@tomer-w and [dependabot[bot]](https://github.com/apps/dependabot)



## 2026.3.10 (2026-03-27)

### Changes

- fix regression in formula metrics not taking enum id

### Contributors

@tomer-w



## 2026.3.9 (2026-03-27)

### Changes


- Fix RuntimeError from asyncio.get\_event\_loop() on Python 3.14 @[copilot-swe-agent[bot]](https://github.com/apps/copilot-swe-agent) (#83)
- fix typo in issue template @dotlambda (#80)
- Add ess max charge power topic @AkarshES (#78)

### Contributors

@AkarshES, @Copilot, @dotlambda, @tomer-w and [copilot-swe-agent[bot]](https://github.com/apps/copilot-swe-agent)



## 2026.3.8 (2026-03-23)

### Changes

- Move enum_values from writable metric to metric. So regaulr sensors expose all possible values.

### Contributors

@tomer-w



## 2026.3.7 (2026-03-20)

### Changes

- Add enum ids which will help with localization
- Fix creation of victron_mqtt to use the new ids

### Contributors

@tomer-w



## 2026.3.6 (2026-03-20)

### Changes

- Minor text tweaks

### Contributors

@tomer-w



## 2026.3.5 (2026-03-20)

### Changes

- Add units for all metrics
- Additional multiRs topics: https://github.com/tomer-w/victron_mqtt/issues/76
- Remove device name from some of the metric names

### ≡ƒº░ Maintenance

- Bump release-drafter/release-drafter from 6 to 7 @[dependabot[bot]](https://github.com/apps/dependabot) (#74)


### Contributors

@dependabot[bot], @tomer-w and [dependabot[bot]](https://github.com/apps/dependabot)



## 2026.3.4 (2026-03-15)

### Changes

- fix: match named placeholders as wildcards in match\_from\_list @bartvanraalte (#75)

### Contributors

@bartvanraalte



## 2026.3.3 (2026-03-07)

### Changes


### ≡ƒº░ Maintenance

- Bump actions/github-script from 7 to 8 @[dependabot[bot]](https://github.com/apps/dependabot) (#70)
- Bump actions/setup-python from 5 to 6 @[dependabot[bot]](https://github.com/apps/dependabot) (#71)
- Bump actions/upload-pages-artifact from 3 to 4 @[dependabot[bot]](https://github.com/apps/dependabot) (#72)
- Bump actions/checkout from 3 to 6 @[dependabot[bot]](https://github.com/apps/dependabot) (#73)

- Bump actions/github-script from 7 to 8 (#70)
- Bump actions/setup-python from 5 to 6 (#71)
- Bump actions/upload-pages-artifact from 3 to 4 (#72)
- Bump actions/checkout from 3 to 6 (#73)
- Modernize async patterns in hub.py
- Add Dependabot config for pip and GitHub Actions updates
- Enable strict ruff lint rules across 22 rule sets
- Add py.typed marker for PEP 561 inline type support
- Increase test coverage to 95% with 73 new tests
- Replace pylint with ruff, add coverage threshold, fix packaging
- Modernize codebase to require Python 3.13+

### Contributors

@dependabot[bot], @tomer-w and [dependabot[bot]](https://github.com/apps/dependabot)



## 2026.3.2 (2026-03-05)

### Changes

- send system device first so via_device will not issue warnning.

### Contributors

@tomer-w



## 2026.3.1 (2026-03-05)

### Changes

- Add multi yield today based on: https://github.com/tomer-w/victron_mqtt/issues/68

### Contributors

@tomer-w



## 2026.3.0 (2026-03-04)

### Changes

- Fix metric type for Cumulative Ah Drawn topic @valimaties (#69)
- align Multi RS Solar topics ids
- Make old cerbos initialize faster
- Linter fixes by copilot
- Improve suppress-republish impl
- Text changes

### Contributors

@tomer-w and @valimaties



## 2026.2.5.1 (2026-02-25)

### Changes

- New topics for battery history @valimaties (#67)

### Contributors

@tomer-w and @valimaties



## 2026.2.4 (2026-02-24)

### Changes

- Bump to 2026.2.4
- Fix tests

### Contributors

@tomer-w



## 2026.2.3 (2026-02-23)

### Changes

- Add support for suppress-republish keepalive message.

### Contributors

@tomer-w



## 2026.2.2 (2026-02-13)

### Changes

- Hub4 AcPowerSetpoint L1-L3 @stixif (#66)

### Contributors

@stixif and @tomer-w



## 2026.2.1 (2026-02-13)

### Changes

- Adding topics for Blue Smart IP22: https://github.com/tomer-w/victron_mqtt/issues/63

### Contributors

@tomer-w



## 2026.2.0 (2026-02-06)

### Changes

- Make metric ids and device ids lowercase
- Improve text

### Contributors

@tomer-w



## 2026.1.8 (2026-01-31)

### Changes

- Better max for ESS BatteryLife schedule charge duration: https://github.com/tomer-w/ha-victron-mqtt/issues/280

### Contributors

@tomer-w



## 2026.1.7 (2026-01-31)

### Changes

- Add inverter PV topics: https://github.com/tomer-w/ha-victron-mqtt/issues/284

### Contributors

@tomer-w



## 2026.1.6 (2026-01-27)

### Changes

- Remove unused persistant state.
- Lot of linter fixes.
- Hub4 Override Setpoint (#62)

### Contributors

@AndyTempel and @tomer-w



## 2026.1.4 (2026-01-17)

### Changes

- Fix tank metric nature

### Contributors

@tomer-w



## 2026.1.3 (2026-01-17)

### Changes

- Reverting the added values to InverterMode
- Lot of linter fixes
- Fix reconnect after connection already made and adding tests: https://github.com/tomer-w/ha-victron-mqtt/issues/276
- Fix tank_remaining to be liters and not metric cube:  https://github.com/tomer-w/victron_mqtt/issues/60

### Contributors

@tomer-w



## 2026.1.2 (2026-01-08)

### Changes

- Fix max ChargeCurrentLimit to be 200. Based on: https://github.com/tomer-w/victron_mqtt/issues/58
- Couple of string fixes

### Contributors

@tomer-w



## 2026.1.1 (2026-01-04)

### Changes

- Change value type from INT to FLOAT for ESS max charge voltage @esquerbatua (#55)
- Add additional InverterMode values base on: https://github.com/tomer-w/victron_mqtt/issues/57

### Contributors

@esquerbatua and @tomer-w



## 2026.1.0 (2026-01-04)

### Changes

- Improve error handling after connection failure to terminate the zombie paho thread.

### Contributors

@tomer-w



## 2025.12.19 (2025-12-28)

### Changes

- Fix crash for Multi RS systems related to bad min and max values: https://github.com/tomer-w/ha-victron-mqtt/issues/266
- fix casing

### Contributors

@tomer-w



## 2025.12.18 (2025-12-27)

### Changes


- Update grid power factor descriptors: add metric nature and increase ΓÇª @glottis512 (#54)
- Support custom name for SwitchableOutput: https://github.com/tomer-w/ha-victron-mqtt/issues/228
- align json
- Add few solar panel tracker topics: https://github.com/tomer-w/ha-victron-mqtt/issues/264
- Update grid power factor descriptors: add metric nature and increase precision (#54)
- Making }/multi/{device_id}/Ess/AcPowerSetpoint writable 
- Exposing Settings/CGwacs/BatteryUse switch

### Contributors

@glottis512 and @tomer-w



## 2025.12.17 (2025-12-20)

### Changes

- Power factor @glottis512 (#53)
- Another evcharger topic from: https://github.com/tomer-w/ha-victron-mqtt/issues/256

### Contributors

@glottis512 and @tomer-w



## 2025.12.16 (2025-12-18)

### Changes


- Split duration and time types.
- Make sure duration sensors are marked as such.

### Contributors

@tomer-w



## 2025.12.15 (2025-12-15)

### Changes

- More text changes

### Contributors

@tomer-w



## 2025.12.14 (2025-12-14)

### Changes

- Export the new AuthenticationError

### Contributors

@tomer-w



## 2025.12.13 (2025-12-14)

### Changes

- Add EV charger session topics: https://github.com/tomer-w/ha-victron-mqtt/issues/256
- Improve error handling to be able to throw AuthenticationError

### Contributors

@tomer-w



## 2025.12.12 (2025-12-11)

### Changes

- Another couple of text fixes

### Contributors

@tomer-w



## 2025.12.11 (2025-12-11)

### Changes

- Fix PowerAssist to be a switch and not a sensor

### Contributors

@tomer-w



## 2025.12.10 (2025-12-11)

### Changes

- More text changes
- Add pre-commit to make sure victron_mqtt.json is up-to-date

### Contributors

@tomer-w



## 2025.12.9 (2025-12-11)

### Changes

- Add sensors + add option to manually trigger test runs @johnmitch (https://github.com/tomer-w/victron_mqtt/pull/52)

### Contributors

@johnmitch



## 2025.12.8 (2025-12-11)

### Changes

- Add sensors + add option to manually trigger test runs @johnmitch (#52)

### Contributors

@johnmitch



## 2025.12.7 (2025-12-11)

### Changes

- Add support for dynamic min/max values based on another metrics. https://github.com/tomer-w/ha-victron-mqtt/issues/242

### Contributors

@tomer-w



## 2025.12.6 (2025-12-10)

### Changes

- More text changes

### Contributors

@tomer-w



## 2025.12.5 (2025-12-10)

### Changes

- More text changes based on HA Core comments

### Contributors

@tomer-w



## 2025.12.4 (2025-12-09)

### Changes

- Adding PowerAssistEnabled per: https://github.com/tomer-w/ha-victron-mqtt/issues/246
- Fix casing based on HA Core feedback

### Contributors

@tomer-w



## 2025.12.3 (2025-12-06)

### Changes

- Remove experimental flag from older topics

### Contributors

@tomer-w



## 2025.12.2 (2025-12-06)

### Changes

- Export test infrastructure

### Contributors

@tomer-w



## 2025.12.1 (2025-12-02)

### Changes

- Fix min value in alternator ChargeCurrentLimit

### Contributors

@tomer-w



## 2025.12.0 (2025-12-02)

### Changes

- Add alternator ChargeCurrentLimit per: https://github.com/tomer-w/ha-victron-mqtt/issues/238

### Contributors

@tomer-w

## 2025.11.6 (2025-11-28)

### Changes


- Add SolarCharger Device Off Reason @ankohanse (#49)
- Add Evcharger status entity @ankohanse (#48)
- Adding MinTemperatureCellId and MaxTemperatureCellId: https://github.com/tomer-w/ha-victron-mqtt/issues/233

### Contributors

@ankohanse and @tomer-w



## 2025.11.5 (2025-11-24)

### Changes

- Adding /Dc/Alternator/Power: https://github.com/tomer-w/ha-victron-mqtt/issues/229
- Add midvoltage data: https://github.com/tomer-w/ha-victron-mqtt/issues/230
- Improve typing for VictronDeviceEnum.from_code

### Contributors

@tomer-w



## 2025.11.4 (2025-11-19)

### Changes

- Fixing DESSRestrictions based on: https://github.com/tomer-w/ha-victron-mqtt/issues/225

### Contributors

@tomer-w



## 2025.11.3 (2025-11-05)

### Changes

- More fixes for virtual switches

### Contributors

@tomer-w



## 2025.11.2 (2025-11-04)

### Changes

- Improve tracing for new writable formulas
- change ESS max charge voltage step to 0.1: https://github.com/tomer-w/ha-victron-mqtt/pull/221

### Contributors

@tomer-w



## 2025.11.1 (2025-11-04)

### Changes

- Add more multi topics: https://github.com/tomer-w/ha-victron-mqtt/issues/218
- Add support for writable virtual entities. Specifically adding a way to enable / disable ESS schedule with a switch: https://github.com/tomer-w/ha-victron-mqtt/issues/210

### Contributors

@tomer-w



## 2025.10.25 (2025-10-31)

### Changes

- Move new BatteryLife/Schedule/Charge metrics to minutes

### Contributors

@tomer-w



## 2025.10.24 (2025-10-31)

### Changes

- Change charge duration to minutes instead of seconds.

### Contributors

@tomer-w



## 2025.10.23 (2025-10-30)

### Changes

- Minor fixes in new schedule topics

### Contributors

@tomer-w



## 2025.10.22 (2025-10-30)

### Changes

- Fix time metric to be writable

### Contributors

@tomer-w



## 2025.10.21 (2025-10-30)

### Changes

- Initial support for time topics and few new CGwacs/BatteryLife/Schedule topics

### Contributors

@tomer-w



## 2025.10.20 (2025-10-30)

### Changes

- Button take three

### Contributors

@tomer-w



## 2025.10.19 (2025-10-29)

### Changes

- Button take two

### Contributors

@tomer-w



## 2025.10.18 (2025-10-29)

### Changes

- Adding Cerbo reboot button

### Contributors

@tomer-w



## 2025.10.17 (2025-10-27)

### Changes

- Stop invalidating metrics based on no new data if the Cerbo is older than 3.5 as it is not honoring the keep alive message. Instead adding logic to invalidate them when there is mqtt disconnect for more than 2 minutes.

### Contributors

@tomer-w



## 2025.10.16 (2025-10-25)

### Changes

- Simplify the code by removing installation id from all ids. It will also make the memory footprint a bit smaller.

### Contributors

@tomer-w



## 2025.10.15 (2025-10-24)

### Changes

- Add acload topics: https://github.com/tomer-w/ha-victron-mqtt/issues/202
- Align all time functions to use time. Monotonic()
- Add (again) the support for old Cerbos that dont sent full_publish_completed. We will wait 45 seconds and assume we got full cycle of messages. Added tests for that to make sure it will not get broken again. https://github.com/tomer-w/ha-victron-mqtt/issues/205

### Contributors

@tomer-w



## 2025.10.14 (2025-10-23)

### Changes

- Support passwords without username: https://github.com/tomer-w/ha-victron-mqtt/issues/200
- Fix max charger current: https://github.com/tomer-w/ha-victron-mqtt/issues/203

### Contributors

@tomer-w

---
*This release was automatically generated from pull requests and commits.*


## 2025.10.12 (2025-10-20)

### Changes


- added topics for /Dc/Pv/Current and for IgnoreAcIn1 @Nortonko (#47)
- Add missing ChargeSchedule values: https://github.com/tomer-w/ha-victron-mqtt/issues/189

### Contributors

@Nortonko and @tomer-w

---
*This release was automatically generated from pull requests and commits.*


## 2025.10.11 (2025-10-15)

### Changes

- Fix ChargeSchedule Disabled to -7

### Contributors

@tomer-w

---
*This release was automatically generated from pull requests and commits.*


## 2025.10.10 (2025-10-15)

### Changes

- Add schedule charge days: https://github.com/tomer-w/ha-victron-mqtt/issues/189

### Contributors

@tomer-w

---
*This release was automatically generated from pull requests and commits.*


## 2025.10.9 (2025-10-14)

### Changes since v2025.10.8

- Fix PhoenixInverterMode.ECO value: https://github.com/tomer-w/victron_mqtt/issues/46

## 2025.10.8 (2025-10-13)

### Changes

* Add Enable/Disable dess control: https://github.com/tomer-w/ha-victron-mqtt/issues/184

### Contributors

@tomer-w


## 2025.10.7 (2025-10-12)

### Changes

- Solarcharger and alternator fixes @iLeeeZi (#44)

### Contributors

@iLeeeZi and @tomer-w


## 2025.10.6 (2025-10-10)

### Changes

* Fix typo: https://github.com/tomer-w/ha-victron-mqtt/pull/179/files
* fix system_dc_pv_power to really be in kWh: https://github.com/tomer-w/ha-victron-mqtt/issues/180

### Contributors

@tomer-w


## 2025.10.5 (2025-10-08)

### Changes

* Remove experimental flags from all current metrics.
* Add support for infinite connect retry

### Contributors

@tomer-w


## 2025.10.4 (2025-10-06)

### Changes

* Implement inverter temperature as requested: https://github.com/tomer-w/ha-victron-mqtt/issues/171

### Contributors

@tomer-w


## 2025.10.3 (2025-10-04)

### Changes

* Fix issue with errors related to duplicate formulas

### Contributors

@tomer-w


## 2025.10.2 (2025-10-03)

### Changes

* Added ScheduledSoc. https://github.com/tomer-w/ha-victron-mqtt/issues/169

### Contributors

@tomer-w


## 2025.10.1 (2025-10-02)

### Changes

* Fix minor test issue

### Contributors

@tomer-w


## 2025.10.0 (2025-09-30)

### Changes

* Add ActiveSocLimit: https://github.com/tomer-w/ha-victron-mqtt/issues/165
* Add dependency between metrics. If it is not found than the metric will not be added. This is good for generator settings which should not show up if there is no generator.
* Filter devices with no metrics.
### Contributors

@tomer-w


## 2025.9.38 (2025-09-29)

### Changes

* GX system heartbeat: https://github.com/tomer-w/ha-victron-mqtt/issues/163
* Fix formula to return data in kWh and not Wh. https://github.com/tomer-w/ha-victron-mqtt/issues/166
* Fix issues with not honoring the defined precision in some cases.

### Contributors

@tomer-w


## 2025.9.37 (2025-09-27)

### Changes

* Fix issue with calling new metric multiple times if we received multiple messages for the same topic before first full publish. Fix: https://github.com/tomer-w/ha-victron-mqtt/issues/153 and https://github.com/tomer-w/ha-victron-mqtt/issues/152

### Contributors

@tomer-w


## 2025.9.36 (2025-09-26)

### Changes

* Improve notification logic

### Contributors

@tomer-w


## 2025.9.35 (2025-09-25)

### Changes

* Fix minimal silence timeout to 60 seconds

### Contributors

@tomer-w


## 2025.9.34 (2025-09-24)

### Changes

* Better error handling in formulas after disconnect.
* Generalize LRS so it will be easier to add more topics

### Contributors

@tomer-w


## 2025.9.33 (2025-09-24)

### Changes

* Move update frequency into the library and update metrics to None value when no data received from MQTT for too long.

### Contributors

@tomer-w


## 2025.9.32 (2025-09-23)

### Changes

* Support pre-release Venus OS versions as requested here: https://github.com/tomer-w/victron_mqtt/issues/41

### Contributors

@tomer-w


## 2025.9.31 (2025-09-23)

### Changes

* Minor changes to new metric names

### Contributors

@tomer-w


## 2025.9.30 (2025-09-22)

### Changes

* Fix the actual formula

### Contributors

@tomer-w


## 2025.9.29 (2025-09-22)

### Changes

* Fix missing name

### Contributors

@tomer-w


## 2025.9.28 (2025-09-22)

### Changes

* Remove formula hacks and simplify logic

### Contributors

@tomer-w


## 2025.9.27 (2025-09-22)

### Changes

* Improve tracing for formula topics

### Contributors

@tomer-w


## 2025.9.26 (2025-09-22)

### Changes

- Initial support for formula entities @tomer-w (#42): https://github.com/tomer-w/ha-victron-mqtt/issues/142

### Contributors

@tomer-w


## 2025.9.25 (2025-09-17)

### Changes

* Minor fix.

### Contributors

@tomer-w


## 2025.9.24 (2025-09-17)

### Changes

* Remove unknown device type for topic warnings: https://github.com/tomer-w/ha-victron-mqtt/issues/148

### Contributors

@tomer-w


## 2025.9.23 (2025-09-17)

### Changes

* Adding heatpump topics based on: https://github.com/tomer-w/ha-victron-mqtt/issues/145

### Contributors

@tomer-w, @apple047


## 2025.9.22 (2025-09-17)

### Changes

* Minor fixes

### Contributors

@tomer-w


## 2025.9.21 (2025-09-17)

### Changes

* Improve Firmware version handling

### Contributors

@tomer-w


## 2025.9.20 (2025-09-17)

### Changes

* Add metrics for VenusOS version and support for cases it is older than v3.5

### Contributors

@tomer-w


## 2025.9.19 (2025-09-15)

### Changes

* Add system_state as described here: https://github.com/tomer-w/ha-victron-mqtt/issues/77

### Contributors

@tomer-w


## 2025.9.18 (2025-09-13)

### Changes

* Fix name embedding with multiple devices

### Contributors

@tomer-w


## 2025.9.17 (2025-09-12)

### Changes

* Bump cell support from 8 to 16.  https://github.com/tomer-w/ha-victron-mqtt/issues/133
* Add more name references. as asked in: https://github.com/tomer-w/ha-victron-mqtt/issues/130

### Contributors

@tomer-w


## 2025.9.15 (2025-09-12)

### Changes

* Fix regression with on_new_metric callback called with the wrong device.

### Contributors

@tomer-w


## 2025.9.14 (2025-09-12)

### Changes

* Fix new regression with None values.

### Contributors

@tomer-w


## 2025.9.13 (2025-09-12)

### Changes

* Adding support for naming entities based on the customname from another entity. Solving: https://github.com/tomer-w/ha-victron-mqtt/issues/60 and https://github.com/tomer-w/ha-victron-mqtt/issues/115
* Now properly fix the resubscribe on reconnect. Also now subscribe to the specific installation id and not + which can lead to problems on systems with multiple Cerbos.
* Add generic_name to victron_mqtt.json file to be used by integration.

### Contributors

@tomer-w


## 2025.9.12 (2025-09-08)

### Changes

* Adding solarcharger per tracker topics based on: https://github.com/tomer-w/ha-victron-mqtt/issues/130
* Implement CustomName per: https://github.com/tomer-w/ha-victron-mqtt/issues/115

### Contributors

@tomer-w


## 2025.9.11 (2025-09-07)

### Changes

* Minor changes to the new Publish function

### Contributors

@tomer-w


## 2025.9.10 (2025-09-07)

### Changes

- Update \_victron\_topics.py @wluke (#39)
- Update \_victron\_enums.py @wluke (#40)
- Fix merges of https://github.com/tomer-w/ha-victron-mqtt/issues/126
- Implement system /Ac/ActiveIn/Source: https://github.com/tomer-w/ha-victron-mqtt/issues/123
- Add MaxFeedInPower: https://github.com/tomer-w/ha-victron-mqtt/issues/124
- Add AcInputLimit and AcExportLimit. Based on: https://github.com/tomer-w/ha-victron-mqtt/issues/125
- More vebus topics based on https://github.com/tomer-w/ha-victron-mqtt/issues/121
- More vebus topics based on https://github.com/tomer-w/ha-victron-mqtt/issues/121

### Contributors

@tomer-w and @wluke


## 2025.9.9 (2025-09-06)

### Changes

* rename Switch to WritableMetric and expose the step property correctly

### Contributors

@tomer-w


## 2025.9.8 (2025-09-06)

### Changes

* change transfer_switch_generator_current_limit to float with 0.1 precision: https://github.com/tomer-w/ha-victron-mqtt/issues/99
* Minor fixes for GPS based on: https://github.com/tomer-w/ha-victron-mqtt/issues/112
* Implement more vebus topics from: https://github.com/tomer-w/ha-victron-mqtt/issues/119
* Sort the topics file for easier maintenance
* Add support for increments

### Contributors

@tomer-w


## 2025.9.7 (2025-09-04)

### Changes

* Fix bug with READ_ONLY mode and is_adjustable_suffix topics

### Contributors

@tomer-w


## 2025.9.6 (2025-09-04)

### Changes

* Minor bug fix.

### Contributors

@tomer-w


## 2025.9.5 (2025-09-04)

### Changes

* Fix hatch test on windows
* Add device type filtering capabilities
* Fix timing test failures
* Implement vebus devices topics as requested: https://github.com/tomer-w/ha-victron-mqtt/issues/116 (in experimental mode only)
* More battery topics as requested here: https://github.com/tomer-w/ha-victron-mqtt/issues/113
* 
### Contributors

@tomer-w


## 2025.9.4 (2025-09-03)

### Changes

* No changes

### Contributors

@tomer-w


## 2025.9.3 (2025-09-03)

### Changes

* Add dcsystem topics based on: https://github.com/tomer-w/ha-victron-mqtt/issues/111
* Move generator settings to its own device (per generator) and map seconds to hours.

### Contributors

@tomer-w


## 2025.9.2 (2025-09-03)

### Changes

- Added topics for solarcharger and inverter @SamLue (#34)
- Add Starter Battery Sensor @mcfrojd (#36)

### Contributors

@SamLue, @mcfrojd and @tomer-w


## 2025.9.1 (2025-09-01)

### Changes

* Initial support for exposing publish service.
* Improve the format of the TopicDescriptor topics to include placeholders and not the mqtt `+`

### Contributors

@tomer-w


## 2025.9.0 (2025-09-01)

### Changes

* More fixes for READ ONLY mode.

### Contributors

@tomer-w


## 2025.8.29 (2025-09-01)

### Changes

* Better implementation for READ_ONLY

### Contributors

@tomer-w


## 2025.8.28 (2025-09-01)

### Changes

* Added topics from: https://github.com/tomer-w/ha-victron-mqtt/issues/99
* Added topics requested here: https://github.com/tomer-w/ha-victron-mqtt/issues/103
* Fixing [Battery Max Charge Voltage should be float instead of integer](https://github.com/tomer-w/ha-victron-mqtt/issues/105)
* Add OperationMode to support read only and experimental modes
* Add support for generator topics. Issue: https://github.com/tomer-w/ha-victron-mqtt/issues/99

### Contributors

@tomer-w


## 2025.8.27 (2025-08-30)

### Changes

* Remove the not used device_type from TopicDescriptor

### Contributors

@tomer-w


## 2025.8.26 (2025-08-29)

### Changes

* Get back the platform to system mapping

### Contributors

@tomer-w


## 2025.8.25 (2025-08-29)

### Changes

* Fix unit_of_measurement for LIQUID_VOLUME

### Contributors

@tomer-w


## 2025.8.24 (2025-08-29)

### Changes

- Export all Grid Frequencies with precission of 2 @msperl (#33)
- Add topics requested on https://github.com/tomer-w/ha-victron-mqtt/issues/96
- Add default values for topics

### Contributors

@msperl and @tomer-w


## 2025.8.23 (2025-08-25)

### Changes

* Fix couple of topics entity type

### Contributors

@tomer-w


## 2025.8.22.1 (2025-08-25)

### Changes

- fstring does not work with quotes in my python deployment @msperl (#32)
- fix handling "empty" VICTRON\_TEST\_ROOT\_PREFIX @msperl (#31)
- More dynamic ess plus epoch support @msperl (#29)

### Contributors

@msperl


## 2025.8.21 (2025-08-23)

### Changes

* Fix crash when the keepalive echo is not ours

### Contributors

@tomer-w


## 2025.8.20 (2025-08-22)

### Changes

* Make sure new metrics callbacks are called only after full refresh, so we have all attributes already handled. Fixing: https://github.com/tomer-w/ha-victron-mqtt/issues/86

### Contributors

@tomer-w


## 2025.8.19 (2025-08-21)

### Changes

- Limit inverter power in ESS @glottis512 (#27)

### Contributors

@glottis512 and @tomer-w


## 2025.8.18 (2025-08-21)

### Changes

- Update \_victron\_topics.py -> DC Voltages precision set to 3 @abroeders (#26)
- Add N/+/settings/+/Settings/CGwacs/BatteryLife/MinimumSocLimit
- Add N/+/battery/+/Voltages/Cell{cell_id(1-4)}
- Make MppOperationMode a sensor and not a switch.
- Update _victron_topics.py -> DC Voltages precision set to 3 ([#26](https://github.com/tomer-w/victron_mqtt/issues/26))
- Fix mqtt connection reset when multiple clients with the same ID connect to the server.
- Add generic mqtt dump utility.


### Contributors

@abroeders and @tomer-w


## 2025.8.17 (2025-08-20)

### Changes

- fix copy/paste error and add explicit unit of % for SOC percentage @msperl (#23)
- add test for duplicate names @msperl (#24)
- Add MaxChargeVoltage, fix MaxChargeCurrent.
- Making settings topics handling more robust. Adding more testing as well.
- Improve logging. Now you can enable debug tracing for specific topic. It helps with debugging missing metrics.

### Contributors

@msperl and @tomer-w


## 2025.8.15 (2025-08-19)

### Changes

* Fix precision issue with GPS data. https://github.com/tomer-w/ha-victron-mqtt/issues/78

### Contributors

@tomer-w


## 2025.8.14 (2025-08-18)

### Changes

- Dynamic DESS additional values @msperl (#20)
- view\_metrics: sort items by id @msperl (#21)
- view\_metrics: take authentication info from envirionment @msperl (#19)

### Contributors

@msperl and @tomer-w


## 2025.8.13 (2025-08-16)

### Changes

* Fix bug with DESS topics
* Add Settings/CGwacs/OvervoltageFeedIn topic
* Add N/+/battery/+/ConsumedAmphours

### Contributors

@tomer-w


## 2025.8.12 (2025-08-16)

### Changes

* Fix bug with DESS topics

### Contributors

@tomer-w


## 2025.8.11 (2025-08-15)

### Changes

* Add DynamicEss strategies topics
* Add solarcharger/MppOperationMode topic
* Add system/Dc/Battery topics
* Add Tank fluid type

### Contributors

@tomer-w


## 2025.8.10 (2025-08-15)

### Changes

* Add Hub.on_new_metric callback

### Contributors

@tomer-w


## 2025.8.9 (2025-08-14)

### Changes

* Apply precision on float values and not just passing it to HA.

### Contributors

@tomer-w


## 2025.8.8 (2025-08-13)

### Changes

* Fail only after 3 connection attempts

### Contributors

@tomer-w


## 2025.8.7 (2025-08-13)

### Changes

* Remove the temp logger code

### Contributors

@tomer-w


## 2025.8.6 (2025-08-13)

### Changes

* Fix tracing regression

### Contributors

@tomer-w


## 2025.8.5 (2025-08-12)

Improve tracing

## 2025.8.4 (2025-08-12)

### Changes

* Fix hang if installation ID is provided.
* Adding ESS max charge current
* Add running client ID

### Contributors

@tomer-w


## 2025.8.3 (2025-08-09)

### Changes

* Make sure not to invoke the callback when metrics value didn't change

### Contributors

@tomer-w


## 2025.8.2 (2025-08-07)

### Changes

* Fix GPS entities to be sensors

### Contributors

@tomer-w


## 2025.8.1 (2025-08-06)

### Changes

- Adding GPS topics @hugo-mcfrojd (#13)
- Improve solarcharger topics
- 
### Contributors

@hugo-mcfrojd and @tomer-w


## 2025.8.0 (2025-08-06)

### Changes

* Remove ASSERT when device_type == DeviceType.UNKNOWN. It is actually expected.

@tomer-w


## 2025.7.34 (2025-08-06)

### Changes

* Improve tracing to detect issue with UNKNOWN device type.

### Contributors

@tomer-w


## 2025.7.33 (2025-08-04)

### Changes

* Fix issue with moving CGWACS to SYSTEM

### Contributors

@tomer-w


## 2025.7.32 (2025-08-04)

### Changes

- Add charge mode for battery @glottis512 (#11)
- Define DC Load @glottis512 (#10)
- Move AcPowerSetPoint to System

### Contributors

@glottis512 and @tomer-w


## 2025.7.31 (2025-08-04)

### Changes

* Fix the SwitchableOutput support.

### Contributors

@tomer-w


## 2025.7.30 (2025-07-30)

### Changes

* Adding initial switch support as requested here: https://github.com/tomer-w/ha-victron-mqtt/issues/29

### Contributors

@tomer-w


## 2025.7.29 (2025-07-30)

### Changes

* Fix issue with Raspberry Pi Venus not sending serial #
* Improve and add entities based on https://github.com/tomer-w/ha-victron-mqtt/pull/39 by @Kieft-C
* Add solar charger state as requested here: https://github.com/tomer-w/ha-victron-mqtt/issues/41
* Add alternator support based on the data supplied here: https://github.com/tomer-w/ha-victron-mqtt/issues/38
* Add solar charger load switch as requested here: https://github.com/tomer-w/ha-victron-mqtt/issues/35

### Contributors
@tomer-w, @Kieft-C


## 2025.7.28 (2025-07-24)

### Changes

* Fixing topics with numbers after last refactor

### Contributors

@tomer-w


## 2025.7.27 (2025-07-24)

### Changes

* Minor bug fix in the new naming logic

### Contributors

@tomer-w


## 2025.7.26 (2025-07-24)

### Changes

* Improve device name logic. No worries, It will not create duplicate devices as I didn't change the IDs.

### Contributors

@tomer-w


## 2025.7.25 (2025-07-24)

### Changes

* Improve support for settings

### Contributors

@tomer-w


## 2025.7.24 (2025-07-23)

### Changes

* Adding support for topic "settings/CGwacs/AcPowerSetPoint"

### Contributors

@tomer-w


## 2025.7.23 (2025-07-23)

### Changes

* Fix bug with UNKNOWN device type as DeviceType enum got out of sync with Victron topics

### Contributors

@tomer-w


## 2025.7.22 (2025-07-23)

### Changes

* Minor text fix

### Contributors

@tomer-w


## 2025.7.21 (2025-07-23)

### Changes

- Adding MultiRsSolar Support @SlapJackNpNp (#9)
- Add support for custom placeholders
- Add (finally) static tests which does not need the Victron simulator

### Contributors

@SlapJackNpNp and @tomer-w


## 2025.7.20 (2025-07-20)

### Changes

* Add missing entities based on @SmartyVan list.

### Contributors

@tomer-w


## 2025.7.19 (2025-07-19)

### Changes

* Add support for custom root topic prefix

### Contributors

@tomer-w


## 2025.7.18 (2025-07-19)

### Changes

* Minor fix

### Contributors

@tomer-w


## 2025.7.17 (2025-07-19)

### Changes

* Add support for dynamic max ranges
* Handling isAdjustable and moving from switch to sensor as needed

### Contributors

@tomer-w


## 2025.7.16 (2025-07-17)

### Changes

* Another fix after phase refactor

### Contributors

@tomer-w


## 2025.7.15 (2025-07-17)

### Changes

* Revert change to MetricType.ENERGY topics

### Contributors

@tomer-w


## 2025.7.14 (2025-07-17)

### Changes

* Fix short_ids not to include upper case characters

### Contributors

@tomer-w


## 2025.7.13 (2025-07-17)

### Changes

* Fix https://github.com/tomer-w/victron_mqtt/issues/5

### Contributors

@tomer-w


## 2025.7.12 (2025-07-17)

### Changes

* Minor bug fix

### Contributors

@tomer-w


## 2025.7.11 (2025-07-17)

### Changes

* Initial refactor for supporting phase and next_phase in topics and names

### Contributors

@tomer-w


## 2025.7.10 (2025-07-16)

### Changes

* No changes

### Contributors

@tomer-w


## 2025.7.9 (2025-07-16)

Release 2025.7.9
-----------------
* Add support for "Generic Temperature Input" by @vitch
* Add some VM-3P75CT topics by @f3nix 
* Add testing to find bugs in topics definition

## 2025.7.8 (2025-07-12)

Fix bug with unique id of device

## 2025.7.7 (2025-07-12)

* Add support for batteries min and max charge. Based on data from @patentuck.
* Make the device type more extensible and format better.

## 2025.7.6-2 (2025-07-12)

* Add support for batteries min and max charge. Based on data from @patentuck.
* Make the device type more extensible and format better.

## 2025.7.5 (2025-07-07)

Bumping version to test downstream workflows

## 2025.7.4 (2025-07-06)

* Moving to Apache License Version 2.0 license 
* Improve sensor's description by @SlapJackNpNp 

## 2025.7.3 (2025-07-04)

Minor fix

## 2025.7.2 (2025-07-03)

Create md file extending the project instructions. Some renames to make things more consistent.

## 2025.7.1 (2025-07-02)

Expose enum string values for metrics

## 2025.7.0 (2025-07-02)

Add Name to definitions so it will be removed from localization

## 2025.6.22 (2025-06-30)

add support for pvinverter by @SlapJackNpNp

