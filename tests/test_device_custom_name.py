"""Tests for writing device custom names through the MQTT transport."""

import json
import logging
from unittest.mock import patch

import pytest
from paho.mqtt.client import MQTTMessageInfo
from paho.mqtt.enums import MQTTErrorCode

from victron_mqtt import NotConnectedError, PublishError
from victron_mqtt.constants import OperationMode
from victron_mqtt.device import Device
from victron_mqtt.hub import Hub

_LOGGER = logging.getLogger(__name__)


@pytest.mark.parametrize("operation_mode", [OperationMode.FULL, OperationMode.EXPERIMENTAL])
@pytest.mark.parametrize("topic_prefix", [None, "bridge"])
@pytest.mark.parametrize(
    ("topic_path", "device_unique_id"),
    [
        ("battery/512/CustomName", "battery_512"),
        ("switch/170/CustomName", "switch_170"),
        ("switch/170/SwitchableOutput/1/Settings/CustomName", "switch_170_output_1"),
        ("switch/170/SwitchableOutput/output_1/Settings/CustomName", "switch_170_output_output_1"),
        ("system/0/SwitchableOutput/ev_connected/Settings/CustomName", "system_0_output_ev_connected"),
    ],
)
@pytest.mark.parametrize("name", ["House battery", "", '  "House" \\ battery  ', "00123", "\u05d1\u05d9\u05ea"])
def test_set_custom_name(
    operation_mode: OperationMode,
    topic_prefix: str | None,
    topic_path: str,
    device_unique_id: str,
    name: str,
) -> None:
    """Writes target the discovered attribute, preserving text and cached state."""
    hub = Hub("localhost", 1883, None, None, False, operation_mode=operation_mode, topic_prefix=topic_prefix)
    topic = f"N/123/{topic_path}"
    hub._handle_normal_message(topic, '{"value": "Old name"}', _LOGGER.debug)
    device = hub._devices[device_unique_id]
    assert device.can_set_custom_name
    result = MQTTMessageInfo(1)
    result.rc = MQTTErrorCode.MQTT_ERR_SUCCESS

    with patch.object(hub._client, "publish", return_value=result) as publish:
        assert device.set_custom_name(name) is None

    expected_topic = f"W/123/{topic_path}"
    if topic_prefix is not None:
        expected_topic = f"{topic_prefix}/{expected_topic}"
    publish.assert_called_once_with(expected_topic, json.dumps({"value": name}))
    assert device.custom_name == "Old name"
    assert device.name == "Old name"

    hub._handle_normal_message(topic, json.dumps({"value": name}), _LOGGER.debug)
    assert device.custom_name == name
    default_name = device.device_type.string
    if device.device_id != "0":
        default_name += f" (ID: {device.device_id})"
    assert device.name == (name or default_name)


@pytest.mark.parametrize("payload", ['{"value": ""}', '{"value": null}'])
def test_custom_name_discovery(payload: str) -> None:
    """An empty name is supported, while a null name does not enable writes."""
    hub = Hub("localhost", 1883, None, None, False)
    topic = "N/123/battery/512/CustomName"
    hub._handle_normal_message("N/123/battery/512/Soc", '{"value": 80}', _LOGGER.debug)
    device = hub._devices["battery_512"]
    assert not device.can_set_custom_name

    with (
        patch.object(hub._client, "publish") as publish,
        pytest.raises(ValueError, match="has not reported a custom name topic"),
    ):
        device.set_custom_name("House battery")
    publish.assert_not_called()

    hub._handle_normal_message(topic, payload, _LOGGER.debug)
    assert device.can_set_custom_name == (payload == '{"value": ""}')

    hub._handle_normal_message(topic, '{"value": "House battery"}', _LOGGER.debug)
    assert device.can_set_custom_name


def test_set_custom_name_read_only() -> None:
    """Read-only mode rejects writes even after discovering the name topic."""
    hub = Hub("localhost", 1883, None, None, False, operation_mode=OperationMode.READ_ONLY)
    hub._handle_normal_message("N/123/battery/512/CustomName", '{"value": "Old name"}', _LOGGER.debug)
    device = hub._devices["battery_512"]
    assert not device.can_set_custom_name

    with patch.object(hub._client, "publish") as publish, pytest.raises(ValueError, match="read-only mode"):
        device.set_custom_name("House battery")
    publish.assert_not_called()
    assert device.custom_name == "Old name"


def test_set_custom_name_without_hub() -> None:
    """The existing standalone Device constructor remains usable."""
    hub = Hub("localhost", 1883, None, None, False)
    hub._handle_normal_message("N/123/battery/512/Soc", '{"value": 80}', _LOGGER.debug)
    placeholder = next(iter(hub._metrics_placeholders.values()))
    device = Device("battery_512", placeholder.parsed_topic, placeholder.topic_descriptor)
    assert not device.can_set_custom_name
    with pytest.raises(ValueError, match="without a hub"):
        device.set_custom_name("House battery")


@pytest.mark.parametrize("name", [None, 123, True])
def test_set_custom_name_invalid_type(name: object) -> None:
    """Invalid input never reaches the MQTT client."""
    hub = Hub("localhost", 1883, None, None, False)
    hub._handle_normal_message("N/123/battery/512/CustomName", '{"value": "Old name"}', _LOGGER.debug)
    device = hub._devices["battery_512"]
    with patch.object(hub._client, "publish") as publish, pytest.raises(TypeError, match="must be a string"):
        device.set_custom_name(name)  # type: ignore[arg-type]
    publish.assert_not_called()


@pytest.mark.parametrize("rc", [MQTTErrorCode.MQTT_ERR_NO_CONN, MQTTErrorCode.MQTT_ERR_QUEUE_SIZE])
def test_set_custom_name_publish_failure(rc: MQTTErrorCode) -> None:
    """Transport failures propagate and do not optimistically rename devices."""
    hub = Hub("localhost", 1883, None, None, False)
    hub._handle_normal_message("N/123/battery/512/CustomName", '{"value": "Old name"}', _LOGGER.debug)
    device = hub._devices["battery_512"]
    result = MQTTMessageInfo(1)
    result.rc = rc
    error_type = NotConnectedError if rc == MQTTErrorCode.MQTT_ERR_NO_CONN else PublishError

    with patch.object(hub._client, "publish", return_value=result) as publish, pytest.raises(error_type):
        device.set_custom_name("House battery")

    publish.assert_called_once_with("W/123/battery/512/CustomName", '{"value": "House battery"}')
    assert device.custom_name == "Old name"
    assert device.name == "Old name"


def test_set_custom_name_parent_and_sub_devices() -> None:
    """Parent and sibling names never change which topic a sub-device writes."""
    hub = Hub("localhost", 1883, None, None, False)
    for path in ["SwitchableOutput/1/Settings/CustomName", "SwitchableOutput/2/Settings/CustomName", "CustomName"]:
        hub._handle_normal_message(f"N/123/switch/170/{path}", '{"value": ""}', _LOGGER.debug)
    parent = hub._devices["switch_170"]
    first = hub._devices["switch_170_output_1"]
    second = hub._devices["switch_170_output_2"]
    assert first._parent_device is parent
    assert second._parent_device is parent
    assert parent.can_set_custom_name
    result = MQTTMessageInfo(1)
    result.rc = MQTTErrorCode.MQTT_ERR_SUCCESS

    with patch.object(hub._client, "publish", return_value=result) as publish:
        first.set_custom_name("First")
        second.set_custom_name("Second")
        parent.set_custom_name("Parent")

    assert [args.args[0] for args in publish.call_args_list] == [
        "W/123/switch/170/SwitchableOutput/1/Settings/CustomName",
        "W/123/switch/170/SwitchableOutput/2/Settings/CustomName",
        "W/123/switch/170/CustomName",
    ]
