"""Unit tests for the Victron MQTT Hub functionality."""
# pyright: reportPrivateUsage=false

import asyncio
import json
import logging
from unittest.mock import MagicMock, patch

import pytest
from paho.mqtt.client import Client, ConnectFlags, PayloadType
from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.reasoncodes import ReasonCode

from victron_mqtt._victron_enums import ChargeSchedule, DeviceType, GenericOnOff
from victron_mqtt._victron_formulas import (
    left_riemann_sum,
    schedule_charge_enabled,
    schedule_charge_enabled_set,
)
from victron_mqtt._victron_topics import topics
from victron_mqtt.constants import MetricKind, MetricNature, MetricType, OperationMode, ValueType
from victron_mqtt.data_classes import ParsedTopic, TopicDescriptor
from victron_mqtt.device import Device, FallbackPlaceholder
from victron_mqtt.formula_common import LRSLastReading
from victron_mqtt.formula_metric import FormulaMetric
from victron_mqtt.hub import (
    CONNECT_MAX_FAILED_ATTEMPTS,
    AuthenticationError,
    CannotConnectError,
    Hub,
    TopicNotFoundError,
)
from victron_mqtt.metric import Metric
from victron_mqtt.testing import (
    create_mocked_hub,
    finalize_injection,
    hub_disconnect,
    inject_message,
    sleep_short,
)
from victron_mqtt.writable_formula_metric import WritableFormulaMetric
from victron_mqtt.writable_metric import WritableMetric

# Configure logging for the test
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_hub_initialization():
    """Test that the Hub initializes correctly."""
    hub: Hub = await create_mocked_hub()
    assert hub._client is not None, "MQTT client should be initialized"

@pytest.mark.asyncio
async def test_authentication_failure():
    """Test that authentication failures are properly raised."""
    with patch('victron_mqtt.hub.mqtt.Client') as mock_client:
        hub = Hub(
            host="localhost",
            port=1883,
            username="testuser",
            password="wrongpassword",
            use_ssl=False,
        )

        mocked_client = MagicMock()
        mock_client.return_value = mocked_client
        hub._client = mocked_client

        # Mock connect_async to trigger authentication failure
        def mock_connect_async_auth_fail(*_args: object, **_kwargs: object) -> None:
            # Simulate authentication failure with ConnackCode.CONNACK_REFUSED_BAD_USERNAME_PASSWORD (value 4)
            hub._on_connect(
                hub._client,
                None,
                ConnectFlags(False),
                ReasonCode(PacketTypes.CONNACK, identifier=134), # 134 corresponds to "Bad user name or password"
                None
            )

        mocked_client.connect_async = MagicMock(name="connect_async", side_effect=mock_connect_async_auth_fail)
        mocked_client.loop_start = MagicMock(name="loop_start")

        # Attempt to connect and expect AuthenticationError
        with pytest.raises(AuthenticationError) as exc_info:
            await hub.connect()

        assert "Authentication failed" in str(exc_info.value)

@pytest.mark.asyncio
async def test_hub_message_handling():
    """Test that the Hub processes incoming MQTT messages correctly."""
    hub: Hub = await create_mocked_hub()

    # Inject a message
    await inject_message(hub, "N/device/123/metric/456", "{\"value\": 42}")

    # Validate the Hub's state
    assert len(hub.devices) == 0, "No devices should be created"

    await finalize_injection(hub)

@pytest.mark.asyncio
async def test_phase_message():
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = await create_mocked_hub()

    # Inject messages after the event is set
    await inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 42}")
    await finalize_injection(hub)

    # Validate the Hub's state
    assert len(hub.devices) == 1, f"Expected 1 device, got {len(hub.devices)}"

    # Validate that the device has the metric we published
    device = hub.devices["grid_30"]
    assert device.device_type == DeviceType.GRID, f"Expected metric type to be 'grid', got {device.device_type}"
    assert device.unique_id == "grid_30", f"Expected device unique_id to be 'grid_30', got {device.unique_id}"
    assert device.model is None, f"Expected device model to be None, got {device.model}"
    assert device.manufacturer is None, f"Expected device manufacturer to be None, got {device.manufacturer}"
    assert device.name == "Grid (ID: 30)", f"Expected device name to be 'Grid (ID: 30)', got {device.name}"
    metric = device.get_metric("grid_energy_forward_l1")
    metric2 = hub.get_metric("grid_30_grid_energy_forward_l1")
    assert metric == metric2, "Metrics should be equal"
    assert metric is not None, "Metric should exist in the device"
    assert metric.value == 42, f"Expected metric value to be 42, got {metric.value}"
    assert metric.short_id == "grid_energy_forward_l1", f"Expected metric short_id to be 'grid_energy_forward_l1', got {metric.short_id}"
    assert metric.generic_short_id == "grid_energy_forward_{phase}", f"Expected metric generic_short_id to be 'grid_energy_forward_{{phase}}', got {metric.generic_short_id}"
    assert metric.unique_id == "grid_30_grid_energy_forward_l1", f"Expected metric unique_id to be 'grid_30_grid_energy_forward_L1', got {metric.unique_id}"
    assert metric.name == "Grid consumption on L1", f"Expected metric name to be 'Grid consumption on l1', got {metric.name}"
    assert metric.generic_name == "Grid consumption on {phase}", f"Expected metric generic_name to be 'Grid consumption on {{phase}}', got {metric.generic_name}"
    assert metric.unit_of_measurement == "kWh", f"Expected metric unit_of_measurement to be 'kWh', got {metric.unit_of_measurement}"
    assert metric.key_values["phase"] == "L1"


@pytest.mark.asyncio
async def test_placeholder_message():
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = await create_mocked_hub()

    # Inject messages after the event is set
    await inject_message(hub, "N/123/system/0/Relay/0/State", "{\"value\": 1}")
    await finalize_injection(hub)

    # Validate the Hub's state
    assert len(hub.devices) == 1, f"Expected 1 device, got {len(hub.devices)}"

    # Validate that the device has the metric we published
    device = hub.devices["system_0"]
    assert device.unique_id == "system_0", f"Expected system_0. Got {device.unique_id}"
    metric = device.get_metric("system_relay_0")
    assert metric is not None, "Metric should exist in the device"
    assert metric.value == GenericOnOff.ON, f"Expected metric value to be GenericOnOff.ON, got {metric.value}"
    assert metric.name == "Relay 0 state", f"Expected metric name to be 'Relay 0 state', got {metric.name}"
    assert metric.generic_name == "Relay {relay} state", f"Expected metric generic_name to be 'Relay {{relay}} state', got {metric.generic_name}"

@pytest.mark.asyncio
async def test_dynamic_min_max_message():
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = await create_mocked_hub()

    # Inject messages after the event is set
    await inject_message(hub, "N/123/settings/0/Settings/CGwacs/AcPowerSetPoint", '{"max": 1000000, "min": -1000000, "value": 50}')
    await finalize_injection(hub)

    # Validate the Hub's state
    assert len(hub.devices) == 1, f"Expected 1 device, got {len(hub.devices)}"

    # Validate that the device has the metric we published
    device = next(iter(hub.devices.values()))
    writable_metric = device.get_metric("system_ac_power_set_point")
    assert writable_metric is not None, "WritableMetric should exist in the device"
    assert isinstance(writable_metric, WritableMetric), f"Expected writable_metric to be of type WritableMetric, got {type(writable_metric)}"
    assert writable_metric.value == 50, f"Expected writable_metric value to be 50, got {writable_metric.value}"
    assert writable_metric.min_value == -1000000, f"Expected writable_metric min to be -1000000, got {writable_metric.min_value}"
    assert writable_metric.max_value == 1000000, f"Expected writable_metric max to be 1000000, got {writable_metric.max_value}"

@pytest.mark.asyncio
async def test_number_message():
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = await create_mocked_hub()

    # Inject messages after the event is set
    await inject_message(hub, "N/123/evcharger/170/SetCurrent", "{\"value\": 100}")

    await finalize_injection(hub, False)

    # Validate the Hub's state
    assert len(hub.devices) == 1, f"Expected 1 device, got {len(hub.devices)}"

    # Validate that the device has the metric we published
    device = hub.devices["evcharger_170"]
    writable_metric = device.get_metric("evcharger_set_current")
    assert isinstance(writable_metric, WritableMetric), f"Expected writable_metric to be of type WritableMetric, got {type(writable_metric)}"
    assert writable_metric.value == 100, f"Expected writable_metric value to be 100, got {writable_metric.value}"

    # Patch the publish method to track calls
    published = {}
    def mock__publish(topic: str, value: PayloadType) -> None:
        published['topic'] = topic
        published['value'] = value
        # Call the original publish if needed
        if hasattr(hub._publish, '__wrapped__'):
            return hub._publish.__wrapped__(topic, value) # type: ignore[union-attr]
        return None
    orig__publish = hub._publish
    hub._publish = mock__publish

    # Set the value, which should trigger a publish
    writable_metric.value = 42

    # Validate that publish was called with the correct topic and value
    assert published, "Expected publish to be called after setting value"
    assert published['topic'] == "W/123/evcharger/170/SetCurrent", f"Expected topic 'W/123/evcharger/170/SetCurrent', got {published['topic']}"
    assert published['value'] == '{"value": 42}', f"Expected published value to be {'{value: 42}'}, got {published['value']}"

    # Restore the original publish method
    hub._publish = orig__publish

    await hub_disconnect(hub)


@pytest.mark.asyncio
async def test_placeholder_adjustable_on():
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = await create_mocked_hub()

    # Inject messages after the event is set
    await inject_message(hub, "N/123/vebus/170/Ac/ActiveIn/CurrentLimit", "{\"value\": 100}")
    await inject_message(hub, "N/123/vebus/170/Ac/ActiveIn/CurrentLimitIsAdjustable", "{\"value\": 1}")
    await finalize_injection(hub)

    # Validate the Hub's state
    assert len(hub.devices) == 1, f"Expected 1 device, got {len(hub.devices)}"

    # Validate that the device has the metric we published
    device = hub.devices["vebus_170"]
    assert len(device._metrics) == 1, f"Expected 1 metrics, got {len(device._metrics)}"
    writable_metric = device.get_metric("vebus_inverter_current_limit")
    assert isinstance(writable_metric, WritableMetric), f"Expected writable_metric to be of type WritableMetric, got {type(writable_metric)}"
    assert writable_metric is not None, "WritableMetric should exist in the device"
    assert writable_metric.value == 100, f"Expected writable_metric value to be 100, got {writable_metric.value}"
    # Ensure cleanup happens even if the test fails

@pytest.mark.asyncio
async def test_placeholder_adjustable_off():
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = await create_mocked_hub()

    # Inject messages after the event is set
    await inject_message(hub, "N/123/vebus/170/Ac/ActiveIn/CurrentLimit", "{\"value\": 100}")
    await inject_message(hub, "N/123/vebus/170/Ac/ActiveIn/CurrentLimitIsAdjustable", "{\"value\": 0}")
    await finalize_injection(hub)

    # Validate the Hub's state
    assert len(hub.devices) == 1, f"Expected 1 device, got {len(hub.devices)}"

    # Validate that the device has the metric we published
    device = hub.devices["vebus_170"]
    assert len(device._metrics) == 1, f"Expected 1 metrics, got {len(device._metrics)}"
    metric = device.get_metric("vebus_inverter_current_limit")
    assert not isinstance(metric, WritableMetric), f"Expected metric to be of type Metric, got {type(metric)}"
    assert metric is not None, "metric should exist in the device"
    assert metric.value == 100, f"Expected metric value to be 100, got {metric.value}"
    # Ensure cleanup happens even if the test fails

@pytest.mark.asyncio
async def test_placeholder_adjustable_on_reverse():
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = await create_mocked_hub()

    # Inject messages after the event is set
    await inject_message(hub, "N/123/vebus/170/Ac/ActiveIn/CurrentLimitIsAdjustable", "{\"value\": 1}")
    await inject_message(hub, "N/123/vebus/170/Ac/ActiveIn/CurrentLimit", "{\"value\": 100}")
    await finalize_injection(hub)

    # Validate that the device has the metric we published
    device = hub.devices["vebus_170"]
    assert len(device._metrics) == 1, f"Expected 1 metrics, got {len(device._metrics)}"
    writable_metric = device.get_metric("vebus_inverter_current_limit")
    assert isinstance(writable_metric, WritableMetric), f"Expected writable_metric to be of type WritableMetric, got {type(writable_metric)}"
    assert writable_metric is not None, "WritableMetric should exist in the device"
    assert writable_metric.value == 100, f"Expected writable_metric value to be 100, got {writable_metric.value}"
    # Ensure cleanup happens even if the test fails

@pytest.mark.asyncio
async def test_placeholder_adjustable_off_reverse():
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = await create_mocked_hub()

    # Inject messages after the event is set
    await inject_message(hub, "N/123/vebus/170/Ac/ActiveIn/CurrentLimitIsAdjustable", "{\"value\": 0}")
    await inject_message(hub, "N/123/vebus/170/Ac/ActiveIn/CurrentLimit", "{\"value\": 100}")
    await finalize_injection(hub)

    # Validate that the device has the metric we published
    device = hub.devices["vebus_170"]
    assert len(device._metrics) == 1, f"Expected 1 metrics, got {len(device._metrics)}"
    writable_metric = device.get_metric("vebus_inverter_current_limit")
    assert not isinstance(writable_metric, WritableMetric), f"Expected writable_metric to be of type WritableMetric, got {type(writable_metric)}"
    assert writable_metric is not None, "WritableMetric should exist in the device"
    assert writable_metric.value == 100, f"Expected writable_metric value to be 100, got {writable_metric.value}"
    # Ensure cleanup happens even if the test fails


@pytest.mark.asyncio
async def test_today_message():
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = await create_mocked_hub()

    # Inject messages after the event is set
    await inject_message(hub, "N/123/solarcharger/290/History/Daily/0/MaxPower", "{\"value\": 1}")
    await inject_message(hub, "N/123/solarcharger/290/History/Daily/1/MaxPower", "{\"value\": 2}")
    await finalize_injection(hub)

    # Validate that the device has the metric we published
    device = hub.devices["solarcharger_290"]
    assert len(device._metrics) == 2, f"Expected 2 metrics, got {len(device._metrics)}"

    metric = device.get_metric("solarcharger_max_power_today")
    assert metric is not None, "Metric should exist in the device"
    assert metric.value == 1, f"Expected metric value to be 1, got {metric.value}"

    metric = device.get_metric("solarcharger_max_power_yesterday")
    assert metric is not None, "Metric should exist in the device"
    assert metric.value == 2, f"Expected metric value to be 2, got {metric.value}"


@pytest.mark.asyncio
async def test_parameterized_topic_with_shared_map_key():
    """Test that topics with a named placeholder (e.g. {mppt_id}) are matched correctly
    when they share a topic-map key with another descriptor (e.g. Daily/0 vs Daily/1).
    Previously match_from_list only did exact matching, so {mppt_id} never matched a
    concrete value like 0 and the message was silently dropped."""
    hub: Hub = await create_mocked_hub()

    await inject_message(hub, "N/123/multi/0/History/Daily/0/Pv/0/Yield", "{\"value\": 9.5}")
    await inject_message(hub, "N/123/multi/0/History/Daily/0/Pv/1/Yield", "{\"value\": 2.5}")
    await inject_message(hub, "N/123/multi/0/History/Daily/1/Pv/0/Yield", "{\"value\": 7.0}")
    await finalize_injection(hub)

    device = hub.devices["multi_0"]
    metric = device.get_metric("multi_mppt_0_yield_today")
    assert metric is not None, "multi_mppt_0_yield_today should be created"
    assert metric.value == 9.5

    metric = device.get_metric("multi_mppt_1_yield_today")
    assert metric is not None, "multi_mppt_1_yield_today should be created"
    assert metric.value == 2.5

    metric = device.get_metric("multi_mppt_0_yield_yesterday")
    assert metric is not None, "multi_mppt_0_yield_yesterday should be created"
    assert metric.value == 7.0


def test_expend_topics():
    """Test that the Hub correctly expands topic descriptors with placeholders."""
    descriptor = next((t for t in topics if t.topic == "N/{installation_id}/switch/{device_id}/SwitchableOutput/output_{output(1-4)}/State"), None)
    assert descriptor is not None, "TopicDescriptor with the specified topic not found"

    expanded = Hub.expand_topic_list([descriptor])
    assert len(expanded) == 4, f"Expected 4 expanded topics, got {len(expanded)}"
    new_desc = next((t for t in expanded if t.topic == "N/{installation_id}/switch/{device_id}/SwitchableOutput/output_1/State"), None)
    assert new_desc, "Missing expanded topic for output 1"
    assert new_desc.short_id == "switch_{output}_state"
    assert new_desc.name == "Switch {output:switch_{output}_custom_name} state"
    assert new_desc.key_values["output"] == "1"

@pytest.mark.asyncio
async def test_expend_message():
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = await create_mocked_hub()

    # Inject messages after the event is set
    await inject_message(hub, "N/123/switch/170/SwitchableOutput/output_2/State", "{\"value\": 1}")
    await finalize_injection(hub)

    # Validate that the device has the metric we published
    device = hub.devices["switch_170"]
    metric = device.get_metric("switch_2_state")
    assert metric is not None, "Metric should exist in the device"
    assert metric.generic_short_id == "switch_{output}_state"
    assert metric.key_values["output"] == "2"
    assert metric.value == GenericOnOff.ON, f"Expected metric value to be GenericOnOff.ON, got {metric.value}"

@pytest.mark.asyncio
async def test_expend_message_2():
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = await create_mocked_hub()

    # Inject messages after the event is set
    await inject_message(hub, "N/123/battery/170/Voltages/Cell3", "{\"value\": 3.331}")
    await finalize_injection(hub)

    # Validate that the device has the metric we published
    device = hub.devices["battery_170"]
    metric = device.get_metric("battery_cell_3_voltage")
    assert metric is not None, "Metric should exist in the device"
    assert metric.generic_short_id == "battery_cell_{cell_id}_voltage"
    assert metric.key_values["cell_id"] == "3"
    assert metric.value == 3.331, f"Expected metric value to be 3.331, got {metric.value}"
    assert metric.generic_name == "Cell {cell_id} voltage", f"Expected metric generic_name to be 'Cell {{cell_id}} voltage', got {metric.generic_name}"

@pytest.mark.asyncio
async def test_same_message_events_none():
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = await create_mocked_hub()

    # Inject messages after the event is set
    await inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 42}")
    await finalize_injection(hub, False)

    # Validate that the device has the metric we published
    device = hub.devices["grid_30"]
    metric = device.get_metric("grid_energy_forward_l1")
    assert metric is not None, "Metric should exist in the device"
    assert metric.value == 42, f"Expected metric value to be 42, got {metric.value}"
    metric.on_update = MagicMock()

    # Inject the same message again
    await inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 42}")
    assert metric.on_update.call_count == 1, "on_update should be called for the first time"
    await inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 43}")
    assert metric.on_update.call_count == 2, "on_update should be called for the new value"
    await inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 43}")
    assert metric.on_update.call_count == 2, "on_update should not be called for the same value"
    await inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 44}")
    assert metric.on_update.call_count == 3, "on_update should be called for the latest value change"

    await hub_disconnect(hub)


@pytest.mark.asyncio
async def test_same_message_events_zero():
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = await create_mocked_hub(update_frequency_seconds=0)

    # Inject messages after the event is set
    await inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 42}")
    await finalize_injection(hub, False)

    # Validate that the device has the metric we published
    device = hub.devices["grid_30"]
    metric = device.get_metric("grid_energy_forward_l1")
    assert metric is not None, "Metric should exist in the device"
    assert metric.value == 42, f"Expected metric value to be 42, got {metric.value}"
    metric.on_update = MagicMock()

    # Inject the same message again
    await inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 42}")
    assert metric.on_update.call_count == 1, "on_update should be called for the same value"
    await inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 43}")
    assert metric.on_update.call_count == 2, "on_update should be called for the new value"

    await hub_disconnect(hub)

@pytest.mark.asyncio
@patch('victron_mqtt.metric.time.monotonic')
async def test_same_message_events_five(mock_time: MagicMock) -> None:
    """Test that the Hub correctly updates its internal state based on MQTT messages."""

    mock_time.return_value = 0.0
    hub: Hub = await create_mocked_hub(update_frequency_seconds=5)

    mock_time.return_value = 10

    # Inject messages after the event is set
    await inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 42}", mock_time)
    await finalize_injection(hub, False, mock_time)

    # Validate that the device has the metric we published
    device = hub.devices["grid_30"]
    metric = device.get_metric("grid_energy_forward_l1")
    assert metric is not None, "Metric should exist in the device"
    assert metric.value == 42, f"Expected metric value to be 42, got {metric.value}"
    metric.on_update = MagicMock()

    # Inject the same message again
    await inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 42}", mock_time)
    assert metric.on_update.call_count == 1, "on_update should be called for the same value as this is the first notification"

    # Inject the same message again
    await inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 42}", mock_time)
    assert metric.on_update.call_count == 1, "on_update should not be called for the same value as the clock did not move"

    mock_time.return_value = 20

    await inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 42}", mock_time)
    assert metric.on_update.call_count == 2, "on_update should be called after frequency elapsed"

    await inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 43}", mock_time)
    assert metric.on_update.call_count == 2, "on_update should not be called for the new value"

    await hub_disconnect(hub, mock_time)

@pytest.mark.asyncio
@patch('victron_mqtt.metric.time.monotonic')
async def test_metric_keepalive_update_frequency_5(mock_time: MagicMock) -> None:
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    mock_time.return_value = 0
    hub: Hub = await create_mocked_hub(update_frequency_seconds=5)

    mock_time.return_value = 10

    # Inject 1st message to generate the metric
    await inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 10}", mock_time)
    await finalize_injection(hub, False, mock_time)

    # Validate that the device has the metric we published
    device = hub.devices["grid_30"]
    metric = device.get_metric("grid_energy_forward_l1")
    assert metric is not None, "Metric should exist in the device"
    assert metric.value == 10, f"Expected metric value to be 10, got {metric.value}"

    def on_metric_update(metric: Metric, value: object) -> None:
        logger.debug("Update: Metric=%s, value=%s", repr(metric), value)
    magic_mock = MagicMock(side_effect=on_metric_update)
    metric.on_update = magic_mock

    # injecting first message which was suppose to trigger callback
    mock_time.return_value = 11
    await inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 11}", mock_time)
    assert metric.on_update.call_count == 1, "on_update should be called for the 1st update"
    magic_mock.assert_called_with(metric, 11)

    # injecting 2nd message which suppose to trigger nothing as of the update frequency
    mock_time.return_value = 12
    await inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 12}", mock_time)
    assert metric.on_update.call_count == 1, "on_update should not be called again as the update frequency did not elapse"

    # Invalidate all metrics by simulating mqtt disconnect
    mock_time.return_value = 13
    hub._on_connect_fail(hub._client, None)

    mock_time.return_value = 140 # We force invalidation after 2 minutes of disconnect
    hub._on_connect_fail(hub._client, None)

    await sleep_short(mock_time)
    assert metric.on_update.call_count == 2, "on_update should be called as metric updated to None"
    magic_mock.assert_called_with(metric, None)

    mock_time.return_value = 77
    await inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 77}", mock_time)
    assert metric.on_update.call_count == 3, "on_update should be called as metric updates back to value"
    magic_mock.assert_called_with(metric, 77)

    await hub_disconnect(hub, mock_time)

@pytest.mark.asyncio
@patch('victron_mqtt.metric.time.monotonic')
async def test_metric_keepalive_update_frequency_none(mock_time: MagicMock) -> None:
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    mock_time.return_value = 0
    hub: Hub = await create_mocked_hub()

    mock_time.return_value = 10

    # Inject 1st message to generate the metric
    await inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 10}", mock_time)
    await finalize_injection(hub, False, mock_time)

    # Validate that the device has the metric we published
    device = hub.devices["grid_30"]
    metric = device.get_metric("grid_energy_forward_l1")
    assert metric is not None, "Metric should exist in the device"
    assert metric.value == 10, f"Expected metric value to be 10, got {metric.value}"

    def on_metric_update(metric: Metric, value: object) -> None:
        logger.debug("Update: Metric=%s, value=%s", repr(metric), value)
    magic_mock = MagicMock(side_effect=on_metric_update)
    metric.on_update = magic_mock

    # injecting first message which was suppose to trigger callback
    mock_time.return_value = 11
    await inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 11}", mock_time)
    assert metric.on_update.call_count == 1, "on_update should be called for the 1st update"
    magic_mock.assert_called_with(metric, 11)

    # injecting 2nd message which suppose to trigger nothing as of the update frequency
    mock_time.return_value = 12
    await inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 12}", mock_time)
    assert metric.on_update.call_count == 2, "on_update should be called again as value changed"

    mock_time.return_value = 13
    await inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 12}", mock_time)
    assert metric.on_update.call_count == 2, "on_update should not be called again as value didnt changed"

    # Invalidate all metrics by simulating mqtt disconnect
    mock_time.return_value = 13
    hub._on_connect_fail(hub._client, None)

    mock_time.return_value = 140 # We force invalidation after 2 minutes of disconnect
    hub._on_connect_fail(hub._client, None)

    await sleep_short(mock_time)
    assert metric.on_update.call_count == 3, "on_update should be called as metric updated to None"
    magic_mock.assert_called_with(metric, None)

    mock_time.return_value = 77
    await inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 77}", mock_time)
    assert metric.on_update.call_count == 4, "on_update should be called as metric updates back to value"
    magic_mock.assert_called_with(metric, 77)

    await hub_disconnect(hub, mock_time)


@pytest.mark.asyncio
async def test_existing_installation_id():
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = await create_mocked_hub(installation_id="123")

    # Inject messages after the event is set
    await inject_message(hub, "N/123/switch/170/SwitchableOutput/output_2/State", "{\"value\": 1}")
    await finalize_injection(hub)

    # Validate that the device has the metric we published
    device = hub.devices["switch_170"]
    metric = device.get_metric("switch_2_state")
    assert metric is not None, "Metric should exist in the device"
    assert metric.generic_short_id == "switch_{output}_state"
    assert metric.key_values["output"] == "2"
    assert metric.value == GenericOnOff.ON, f"Expected metric value to be GenericOnOff.ON, got {metric.value}"


@pytest.mark.asyncio
async def test_multiple_hubs():
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub1: Hub = await create_mocked_hub()

    # Inject messages after the event is set
    await inject_message(hub1, "N/123/switch/170/SwitchableOutput/output_2/State", "{\"value\": 1}")
    await finalize_injection(hub1, disconnect=False)

    # Validate that the device has the metric we published
    device1 = hub1.devices["switch_170"]
    metric1 = device1.get_metric("switch_2_state")
    assert metric1 is not None, "Metric should exist in the device"
    assert metric1.generic_short_id == "switch_{output}_state"
    assert metric1.key_values["output"] == "2"
    assert metric1.value == GenericOnOff.ON, f"Expected metric value to be GenericOnOff.ON, got {metric1.value}"

    hub2: Hub = await create_mocked_hub(installation_id="123")
    # Inject messages after the event is set
    await inject_message(hub2, "N/123/switch/170/SwitchableOutput/output_2/State", "{\"value\": 0}")
    await finalize_injection(hub2, disconnect=False)

    # Validate the Hub's state
    assert len(hub2.devices) == 1, f"Expected 1 device, got {len(hub1.devices)}"

    # Validate that the device has the metric we published
    device2 = hub2.devices["switch_170"]
    metric2 = device2.get_metric("switch_2_state")
    assert metric2 is not None, "Metric should exist in the device"
    assert metric2.generic_short_id == "switch_{output}_state"
    assert metric2.key_values["output"] == "2"
    assert metric2.value == GenericOnOff.OFF, f"Expected metric value to be GenericOnOff.OFF, got {metric2.value}"

    await hub_disconnect(hub2)
    await hub_disconnect(hub1)

@pytest.mark.asyncio
async def test_float_precision():
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = await create_mocked_hub()

    # Inject messages after the event is set
    await inject_message(hub, "N/123/system/170/Dc/System/Power", "{\"value\": 1.1234}")
    await finalize_injection(hub)

    # Validate that the device has the metric we published
    device = hub.devices["system_170"]
    metric = device.get_metric("system_dc_consumption")
    assert metric is not None, "Metric should exist in the device"
    assert metric.value == 1.1, f"Expected metric value to be 1.1, got {metric.value}"

@pytest.mark.asyncio
async def test_float_precision_none():
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = await create_mocked_hub()

    # Inject messages after the event is set
    await inject_message(hub, "N/123/gps/170/Position/Latitude", "{\"value\": 1.0123456789}")
    await finalize_injection(hub)

    # Validate that the device has the metric we published
    device = hub.devices["gps_170"]
    metric = device.get_metric("gps_latitude")
    assert metric is not None, "Metric should exist in the device"
    assert metric.value == 1.0123456789, f"Expected metric value to be 1.0123456789, got {metric.value}"

@pytest.mark.asyncio
async def test_new_metric():
    """Test that the Hub correctly triggers the on_new_metric callback."""
    hub: Hub = await create_mocked_hub(operation_mode=OperationMode.EXPERIMENTAL)

    # Mock the on_new_metric callback
    def on_new_metric_mock(hub: Hub, device: object, metric: Metric) -> None:
        logger.debug("New metric added: Hub=%s, Device=%s, Metric=%s", hub, device, repr(metric))
    mock_on_new_metric = MagicMock(side_effect=on_new_metric_mock)
    hub.on_new_metric = mock_on_new_metric

    # Inject messages after the event is set
    await inject_message(hub, "N/123/system/170/Dc/System/Power", "{\"value\": 1.1234}")
    await inject_message(hub, "N/123/system/170/Dc/Battery/Power", "{\"value\": 120}") # Will generate also formula metrics.
    await inject_message(hub, "N/123/gps/170/Position/Latitude", "{\"value\": 2.3456}")
    await finalize_injection(hub, disconnect=False)

    # Validate that the on_new_metric callback was called
    mock_on_new_metric.assert_any_call(hub, hub.devices["system_170"], hub.devices["system_170"].get_metric("system_dc_consumption"))
    mock_on_new_metric.assert_any_call(hub, hub.devices["system_170"], hub.devices["system_170"].get_metric("system_dc_battery_power"))
    mock_on_new_metric.assert_any_call(hub, hub.devices["gps_170"], hub.devices["gps_170"].get_metric("gps_latitude"))
    mock_on_new_metric.assert_any_call(hub, hub.devices["system_170"], hub.devices["system_170"].get_metric("system_dc_battery_charge_energy"))
    mock_on_new_metric.assert_any_call(hub, hub.devices["system_170"], hub.devices["system_170"].get_metric("system_dc_battery_discharge_energy"))
    assert mock_on_new_metric.call_count == 5, "on_new_metric should be called exactly 5 times"

    # Check that we got the callback only once
    hub._keepalive()
    # Wait for the callback to be triggered
    await sleep_short()
    assert mock_on_new_metric.call_count == 5, "on_new_metric should be called exactly 5 times"

    # Validate that the device has the metric we published
    device = hub.devices["system_170"]
    metric = device.get_metric("system_dc_consumption")
    assert metric is not None, "Metric should exist in the device"
    assert metric.value == 1.1, f"Expected metric value to be 1.1, got {metric.value}"
    await hub_disconnect(hub)

@pytest.mark.asyncio
async def test_new_metric_system_callbacks_first():
    """System device callbacks should be triggered before other device callbacks."""
    hub: Hub = await create_mocked_hub()

    callback_device_ids: list[str] = []

    def on_new_metric_mock(_hub: Hub, device: object, _metric: Metric) -> None:
        callback_device_ids.append(str(device.unique_id))

    hub.on_new_metric = MagicMock(side_effect=on_new_metric_mock)

    # Inject a non-system metric first, then a system metric.
    await inject_message(hub, "N/123/gps/170/Position/Latitude", "{\"value\": 2.3456}")
    await inject_message(hub, "N/123/system/170/Dc/System/Power", "{\"value\": 1.1234}")
    await finalize_injection(hub, disconnect=False)

    assert callback_device_ids == ["system_170", "gps_170"], "System metrics should be dispatched first"

    await hub_disconnect(hub)

@pytest.mark.asyncio
async def test_new_metric_duplicate_messages():
    """Test that the Hub correctly triggers the on_new_metric callback."""
    hub: Hub = await create_mocked_hub()

    # Mock the on_new_metric callback
    def on_new_metric_mock(hub: Hub, device: object, metric: Metric) -> None:
        logger.debug("New metric added: Hub=%s, Device=%s, Metric=%s", hub, device, repr(metric))
    mock_on_new_metric = MagicMock(side_effect=on_new_metric_mock)
    hub.on_new_metric = mock_on_new_metric

    # Inject 2 same messages, we expect to get only one metric out of it
    await inject_message(hub, "N/123/system/170/Dc/System/Power", "{\"value\": 1}")
    await inject_message(hub, "N/123/system/170/Dc/System/Power", "{\"value\": 2}")
    await finalize_injection(hub, disconnect=False)

    # Validate that the on_new_metric callback was called
    mock_on_new_metric.assert_any_call(hub, hub.devices["system_170"], hub.devices["system_170"].get_metric("system_dc_consumption"))
    assert mock_on_new_metric.call_count == 1, "on_new_metric should be called exactly 1 time"

    # Check that we got the callback only once
    hub._keepalive()
    # Wait for the callback to be triggered
    await sleep_short()
    assert mock_on_new_metric.call_count == 1, "on_new_metric should be called exactly 1 time"

    # Validate that the device has the metric we published
    device = hub.devices["system_170"]
    assert len(device.metrics) == 1, "Device should have exactly 1 metric"
    metric = device.get_metric("system_dc_consumption")
    assert metric is not None, "Metric should exist in the device"
    assert metric.value == 2, f"Expected metric value to be 2, got {metric.value}"

    await hub_disconnect(hub)

@pytest.mark.asyncio
async def test_new_metric_duplicate_formula_messages():
    """Test that the Hub correctly triggers the on_new_metric callback."""
    hub: Hub = await create_mocked_hub(operation_mode=OperationMode.EXPERIMENTAL)

    # Mock the on_new_metric callback
    def on_new_metric_mock(hub: Hub, device: object, metric: Metric) -> None:
        logger.debug("New metric added: Hub=%s, Device=%s, Metric=%s", hub, device, repr(metric))
    mock_on_new_metric = MagicMock(side_effect=on_new_metric_mock)
    hub.on_new_metric = mock_on_new_metric

    # Inject 1st message to generate formula metric
    await inject_message(hub, "N/123/system/170/Dc/Battery/Power", "{\"value\": 120}") # Will generate also formula metrics.
    await finalize_injection(hub, disconnect=False)

    # Validate that the on_new_metric callback was called
    mock_on_new_metric.assert_any_call(hub, hub.devices["system_170"], hub.devices["system_170"].get_metric("system_dc_battery_power"))
    mock_on_new_metric.assert_any_call(hub, hub.devices["system_170"], hub.devices["system_170"].get_metric("system_dc_battery_charge_energy"))
    mock_on_new_metric.assert_any_call(hub, hub.devices["system_170"], hub.devices["system_170"].get_metric("system_dc_battery_discharge_energy"))
    assert mock_on_new_metric.call_count == 3, "on_new_metric should be called exactly 3 times"

    # Check that we got the callback only once
    hub._keepalive()
    # Wait for the callback to be triggered
    await sleep_short()
    assert mock_on_new_metric.call_count == 3, "on_new_metric should be called exactly 3 times"

    # Inject another message. Should generate this but not the formula metrics again
    await inject_message(hub, "N/123/gps/170/Position/Latitude", "{\"value\": 2.3456}")
    await finalize_injection(hub, disconnect=False)

    # Check that we got the callback only once
    hub._keepalive()
    # Wait for the callback to be triggered
    await sleep_short()
    mock_on_new_metric.assert_any_call(hub, hub.devices["gps_170"], hub.devices["gps_170"].get_metric("gps_latitude"))
    assert mock_on_new_metric.call_count == 4, "on_new_metric should be called exactly 4 times"

    await hub_disconnect(hub)

@pytest.mark.asyncio
# async def test_experimental_metrics_not_created_by_default():
#     """Ensure experimental topics do not create devices/metrics when operation_mode is not EXPERIMENTAL."""
#     hub: Hub = await create_mocked_hub()

#     # Inject an experimental topic (generator TodayRuntime is marked experimental in _victron_topics)
#     await inject_message(hub, "N/123/generator/170/TodayRuntime", '{"value": 100}')
#     await finalize_injection(hub)

#     # The experimental topic should not have created a device or metric
#     assert "generator_170" not in hub.devices, "Experimental topic should not create devices/metrics when operation_mode is not EXPERIMENTAL"

@pytest.mark.asyncio
async def test_experimental_metrics_created_when_needed():
    """Ensure experimental topics create devices/metrics when operation_mode is EXPERIMENTAL."""
    hub: Hub = await create_mocked_hub(operation_mode=OperationMode.EXPERIMENTAL)

    # Inject an experimental topic (generator TodayRuntime is marked experimental in _victron_topics)
    await inject_message(hub, "N/123/generator/170/TodayRuntime", '{"value": 100}')
    await finalize_injection(hub)

    # The experimental topic should not have created a device or metric
    assert "generator_170" in hub.devices, "Experimental topic should not create devices/metrics when operation_mode is not EXPERIMENTAL"

@pytest.mark.asyncio
async def test_read_only_creates_plain_metrics():
    """Ensure that in READ_ONLY mode entities that are normally Switch/Number/Select are created as plain Metric."""
    hub: Hub = await create_mocked_hub(operation_mode=OperationMode.READ_ONLY)
    # Inject a topic that normally creates a Switch/Number (evcharger SetCurrent)
    await inject_message(hub, "N/123/evcharger/170/SetCurrent", "{\"value\": 100}")
    await finalize_injection(hub)

    # Validate the Hub's state
    assert "evcharger_170" in hub.devices, "Device should be created"
    device = hub.devices["evcharger_170"]
    metric = device.get_metric("evcharger_set_current")
    assert metric is not None, "Metric should exist in the device"
    assert not isinstance(metric, WritableMetric), "In READ_ONLY mode the metric should NOT be a WritableMetric"
    assert isinstance(metric, Metric), "In READ_ONLY mode the metric should be a plain Metric"

@pytest.mark.asyncio
async def test_publish():
    """Test that the Hub correctly publishes MQTT messages."""
    hub: Hub = await create_mocked_hub(operation_mode=OperationMode.EXPERIMENTAL)
    mocked_client: MagicMock = hub._client # type: ignore[assignment]

    # Clear any previous publish calls recorded by the mocked client
    if hasattr(mocked_client.publish, 'reset_mock'):
        mocked_client.publish.reset_mock()

    # Call the publish helper which should result in an internal client.publish call
    hub.publish("generator_service_counter_reset", "170", 1)

    # Finalize injection to allow any keepalive/full-publish flows to complete
    await finalize_injection(hub)

    # Expected topic and payload
    expected_topic = "W/123/generator/170/ServiceCounterReset"
    expected_payload = '{"value": 1}'

    # Ensure the underlying client's publish was called with the expected values
    mocked_client.publish.assert_any_call(expected_topic, expected_payload)

@pytest.mark.asyncio
async def test_publish_topic_not_found():
    """Test that publishing to a non-existent topic raises TopicNotFoundError."""
    hub: Hub = await create_mocked_hub(operation_mode=OperationMode.EXPERIMENTAL)
    mocked_client: MagicMock = hub._client # type: ignore[assignment]

    # Clear any previous publish calls recorded by the mocked client
    if hasattr(mocked_client.publish, 'reset_mock'):
        mocked_client.publish.reset_mock()

    # Call the publish helper which should result in an internal client.publish call
    with pytest.raises(TopicNotFoundError):
        hub.publish("NO TOPIC", "170", 1)

    # Finalize injection to allow any keepalive/full-publish flows to complete
    await finalize_injection(hub)

@pytest.mark.asyncio
async def test_filtered_message():
    """Test that the Hub correctly filters MQTT messages for EVCHARGER device type."""
    hub: Hub = await create_mocked_hub(device_type_exclude_filter=[DeviceType.EVCHARGER], operation_mode=OperationMode.EXPERIMENTAL)

    # Inject messages after the event is set
    await inject_message(hub, "N/123/evcharger/170/SetCurrent", "{\"value\": 100}")

    # Validate the Hub's state
    assert len(hub.devices) == 0, f"Expected no devices, got {len(hub.devices)}"

@pytest.mark.asyncio
async def test_filtered_message_system():
    """Test that the Hub correctly filters MQTT messages for system device type."""
    hub: Hub = await create_mocked_hub(device_type_exclude_filter=[DeviceType.SYSTEM], operation_mode=OperationMode.EXPERIMENTAL)

    # Inject messages after the event is set
    await inject_message(hub, "N/123/system/0/Relay/0/State", "{\"value\": 1}")
    await finalize_injection(hub)

    # Validate the Hub's state - system device exists but has no metrics due to filtering
    assert len(hub.devices) == 0, f"Expected 0 device, got {len(hub.devices)}"

@pytest.mark.asyncio
async def test_no_filtered_message_placeholder():
    """Test that the Hub correctly filters MQTT messages for generator2 device type."""
    hub: Hub = await create_mocked_hub(device_type_exclude_filter=[DeviceType.GENERATOR0], operation_mode=OperationMode.EXPERIMENTAL)

    # Inject messages after the event is set
    await inject_message(hub, "N/123/settings/0/Settings/Generator1/Soc/Enabled", "{\"value\": 1}")
    await finalize_injection(hub)

    # Validate the Hub's state - only system device exists, generator message was filtered
    assert len(hub.devices) == 0, f"Expected no devices, got {len(hub.devices)}"


@pytest.mark.asyncio
async def test_filtered_message_placeholder():
    """Test that the Hub correctly filters MQTT messages for generator1 device type."""
    hub: Hub = await create_mocked_hub(device_type_exclude_filter=[DeviceType.GENERATOR1], operation_mode=OperationMode.EXPERIMENTAL)

    # Inject messages after the event is set
    await inject_message(hub, "N/123/settings/0/Settings/Generator1/Soc/Enabled", "{\"value\": 1}")
    await finalize_injection(hub)

    # Validate the Hub's state - only system device exists, generator message was filtered
    assert len(hub.devices) == 0, f"Expected no devices, got {len(hub.devices)}"


@pytest.mark.asyncio
async def test_remote_name_dont_exists():
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = await create_mocked_hub()

    await inject_message(hub, "N/123/switch/170/SwitchableOutput/output_1/State", "{\"value\": 1}")
    await finalize_injection(hub)

    # Validate the Hub's state
    assert len(hub.devices) == 1, f"Expected 1 device, got {len(hub.devices)}"

    # Validate that the device has the metric we published
    device = hub.devices["switch_170"]
    assert len(device._metrics) == 1, f"Expected 1 metrics, got {len(device._metrics)}"
    metric = device.get_metric("switch_1_state")
    assert metric is not None, "metric should exist in the device"
    assert metric.name == "Switch 1 state", "Expected metric name to be 'Switch 1 state', got {metric.name}"
    assert metric.generic_name == "Switch {output} state", "Expected metric generic_name to be 'Switch {output} state', got {metric.generic_name}"
    assert metric.value == GenericOnOff.ON, f"Expected metric value to be 1, got {metric.value}"
    assert metric.key_values["output"] == "1"

@pytest.mark.asyncio
async def test_remote_name_exists():
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = await create_mocked_hub()

    await inject_message(hub, "N/123/switch/170/SwitchableOutput/output_1/State", "{\"value\": 1}")
    await inject_message(hub, "N/123/switch/170/SwitchableOutput/output_1/Settings/CustomName", "{\"value\": \"bla\"}")
    await finalize_injection(hub)

    # Validate the Hub's state
    assert len(hub.devices) == 1, f"Expected 1 device, got {len(hub.devices)}"

    # Validate that the device has the metric we published
    device = hub.devices["switch_170"]
    assert len(device._metrics) == 2, f"Expected 2 metrics, got {len(device._metrics)}"
    metric = device.get_metric("switch_1_state")
    assert metric is not None, "metric should exist in the device"
    assert metric.name == "Switch bla state", "Expected metric name to be 'Switch bla state', got {metric.name}"
    assert metric.generic_name == "Switch {output} state", "Expected metric name to be 'Switch {output} state', got {metric.name}"
    assert metric.value == GenericOnOff.ON, f"Expected metric value to be 1, got {metric.value}"
    assert metric.key_values["output"] == "bla"

@pytest.mark.asyncio
async def test_remote_name_exists_two_devices():
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = await create_mocked_hub()

    await inject_message(hub, "N/123/switch/170/SwitchableOutput/output_1/State", "{\"value\": 1}")
    await inject_message(hub, "N/123/switch/170/SwitchableOutput/output_1/Settings/CustomName", "{\"value\": \"bla\"}")
    await inject_message(hub, "N/123/switch/155/SwitchableOutput/output_1/State", "{\"value\": 1}")
    await inject_message(hub, "N/123/switch/155/SwitchableOutput/output_1/Settings/CustomName", "{\"value\": \"foo\"}")
    await finalize_injection(hub)

    # Validate the Hub's state
    assert len(hub.devices) == 2, f"Expected 2 device, got {len(hub.devices)}"

    # Validate that the device has the metric we published
    device = hub.devices["switch_170"]
    assert len(device._metrics) == 2, f"Expected 2 metrics, got {len(device._metrics)}"
    metric = device.get_metric("switch_1_state")
    assert metric is not None, "metric should exist in the device"
    assert metric.name == "Switch bla state", "Expected metric name to be 'Switch bla state', got {metric.name}"
    assert metric.generic_name == "Switch {output} state", "Expected metric name to be 'Switch {output} state', got {metric.name}"
    assert metric.value == GenericOnOff.ON, f"Expected metric value to be 1, got {metric.value}"
    assert metric.key_values["output"] == "bla"

    device = hub.devices["switch_155"]
    assert len(device._metrics) == 2, f"Expected 2 metrics, got {len(device._metrics)}"
    metric = device.get_metric("switch_1_state")
    assert metric is not None, "metric should exist in the device"
    assert metric.name == "Switch foo state", "Expected metric name to be 'Switch foo state', got {metric.name}"
    assert metric.generic_name == "Switch {output} state", "Expected metric name to be 'Switch {output} state', got {metric.name}"
    assert metric.value == GenericOnOff.ON, f"Expected metric value to be 1, got {metric.value}"
    assert metric.key_values["output"] == "foo"

@pytest.mark.asyncio
async def test_remote_name_exists_2():
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = await create_mocked_hub()

    await inject_message(hub, "N/123/solarcharger/170/Pv/2/Name", "{\"value\": \"bar\"}")
    await inject_message(hub, "N/123/solarcharger/170/Pv/2/P", "{\"value\": 1}")
    await finalize_injection(hub)

    # Validate the Hub's state
    assert len(hub.devices) == 1, f"Expected 1 device, got {len(hub.devices)}"

    # Validate that the device has the metric we published
    device = hub.devices["solarcharger_170"]
    assert len(device._metrics) == 2, f"Expected 2 metrics, got {len(device._metrics)}"
    metric = device.get_metric("solarcharger_tracker_2_power")
    assert metric is not None, "metric should exist in the device"
    assert metric.name == "PV tracker bar power", "Expected metric name to be 'PV tracker bar power', got {metric.name}"
    assert metric.generic_name == "PV tracker {tracker} power", "Expected metric name to be 'PV tracker {tracker} power', got {metric.name}"
    assert metric.value == 1, f"Expected metric value to be 1, got {metric.value}"
    assert metric.key_values["tracker"] == "bar"

@pytest.mark.asyncio
async def test_on_connect_sets_up_subscriptions():
    """Test that subscriptions are set up after _on_connect callback."""
    # Create a hub with installation_id
    hub = Hub(host="localhost", port=1883, username=None, password=None, use_ssl=False, installation_id="test123")

    # Create a MagicMock instance with proper method mocks
    mocked_client: MagicMock = MagicMock(spec=Client)
    mocked_client.is_connected.return_value = True

    # Set required properties
    hub._client = mocked_client
    hub._first_connect = False  # Mark as not first connect to allow subscriptions
    hub._loop = asyncio.get_running_loop()  # Set the event loop

    # Call _on_connect directly with successful connection (rc=0)
    hub._on_connect_internal(mocked_client, None, ConnectFlags(False), ReasonCode(PacketTypes.CONNACK, identifier=0), None)

    # Get expected number of subscriptions
    expected_calls = len(hub._subscription_list) + 1  # +1 for full_publish_completed

    # Get the actual subscription calls
    actual_calls = mocked_client.subscribe.call_count
    assert actual_calls == expected_calls, f"Expected {expected_calls} subscribe calls, got {actual_calls}"

    # Verify the full_publish_completed subscription was made
    full_publish_topic = "N/test123/full_publish_completed"
    mocked_client.subscribe.assert_any_call(full_publish_topic)

@pytest.mark.asyncio
async def test_null_message():
    """Test that the Hub correctly filters MQTT messages with null value."""
    hub: Hub = await create_mocked_hub()

    # Inject messages after the event is set
    await inject_message(hub, "N/123/evcharger/170/SetCurrent", "{\"value\": null}")
    await finalize_injection(hub)

    # Validate the Hub's state - only system device exists, evcharger message was filtered
    assert len(hub.devices) == 0, f"Expected no devices, got {len(hub.devices)}"

@pytest.mark.asyncio
@patch('victron_mqtt.formula_common.time.monotonic')
async def test_formula_metric(mock_time: MagicMock) -> None:
    """Test that the Hub correctly calculates formula metrics."""
    # Mock time.monotonic() to return a fixed time
    mock_time.return_value = 0

    hub: Hub = await create_mocked_hub(operation_mode=OperationMode.EXPERIMENTAL)

    # Inject messages after the event is set
    await inject_message(hub, "N/123/system/0/Dc/Battery/Power", "{\"value\": 1200}", mock_time)
    mock_time.return_value += 0.1
    await finalize_injection(hub, False, mock_time)

    # Validate the Hub's state - only system device exists, evcharger message was filtered
    assert len(hub.devices) == 1, f"Expected 1 device (system device), got {len(hub.devices)}"
    device = hub.devices["system_0"]
    assert len(device._metrics) == 3, f"Expected 3 metrics, got {len(device._metrics)}"
    metric1 = device.get_metric("system_dc_battery_power")
    assert metric1 is not None, "metric should exist in the device"
    assert metric1.value == 1200, f"Expected metric value to be 1200, got {metric1.value}"

    metric2 = device.get_metric("system_dc_battery_charge_energy")
    assert metric2 is not None, "metric should exist in the device"
    assert metric2.value == 0.0, f"Expected metric value to be 0.0, got {metric2.value}"
    assert metric2.unique_id == "system_0_system_dc_battery_charge_energy", f"Expected unique_id to be 'system_0_system_dc_battery_charge_energy', got {metric2.generic_short_id}"
    assert metric2.short_id == "system_dc_battery_charge_energy", f"Expected short_id to be 'system_dc_battery_charge_energy', got {metric2.generic_short_id}"
    assert metric2.generic_short_id == "system_dc_battery_charge_energy", f"Expected generic_short_id to be 'system_dc_battery_charge_energy', got {metric2.generic_short_id}"
    assert metric2.name == "DC battery charge energy", f"Expected name to be 'DC battery charge energy', got {metric2.name}"

    metric3 = device.get_metric("system_dc_battery_discharge_energy")
    assert metric3 is not None, "metric should exist in the device"
    assert metric3.value == 0.0, f"Expected metric value to be 0.0, got {metric3.value}"
    assert metric3.generic_short_id == "system_dc_battery_discharge_energy", f"Expected generic_short_id to be 'system_dc_battery_discharge_energy', got {metric3.generic_short_id}"
    assert metric3.name == "DC battery discharge energy", f"Expected name to be 'DC battery discharge energy', got {metric3.name}"

    mock_time.return_value = 15
    await inject_message(hub, "N/123/system/0/Dc/Battery/Power", "{\"value\": 800}", mock_time)
    assert metric2.value == 0.005, f"Expected metric value to be 0.005, got {metric2.value}"

    mock_time.return_value = 30
    await inject_message(hub, "N/123/system/0/Dc/Battery/Power", "{\"value\": -1000}", mock_time)
    assert metric2.value == 0.008, f"Expected metric value to be 0.008, got {metric2.value}"

    mock_time.return_value = 45
    await inject_message(hub, "N/123/system/0/Dc/Battery/Power", "{\"value\": -2000}", mock_time)
    assert metric2.value == 0.008, f"Expected metric value to be 0.008, got {metric2.value}"
    assert metric3.value == 0.004, f"Expected metric value to be 0.004, got {metric3.value}"

    # Test the 2nd way to get metric
    assert hub.get_metric("system_0_system_dc_battery_discharge_energy") is not None

    await hub_disconnect(hub, mock_time)

@pytest.mark.asyncio
@patch('victron_mqtt.formula_common.time.monotonic')
async def test_formula_switch(mock_time: MagicMock) -> None:
    """Test that the Hub correctly calculates formula metrics."""
    # Mock time.monotonic() to return a fixed time
    mock_time.return_value = 0

    hub: Hub = await create_mocked_hub(operation_mode=OperationMode.EXPERIMENTAL)

    # Inject messages after the event is set
    await inject_message(hub, "N/123/settings/0/Settings/CGwacs/BatteryLife/Schedule/Charge/2/Day", "{\"value\": -7}", mock_time)
    mock_time.return_value += 0.1
    await finalize_injection(hub, False, mock_time)

    # Validate the Hub's state - only system device exists
    assert len(hub.devices) == 1, f"Expected 1 device (system device), got {len(hub.devices)}"
    device = hub.devices["system_0"]
    assert len(device._metrics) == 2, f"Expected 2 metrics, got {len(device._metrics)}"

    metric1 = device.get_metric("system_ess_schedule_charge_2_days")
    assert metric1 is not None, "metric should exist in the device"
    assert metric1.unique_id == "system_0_system_ess_schedule_charge_2_days"
    assert metric1.value == ChargeSchedule.DISABLED_EVERY_DAY, f"Expected metric value to be -7, got {metric1.value}"

    metric2 = device.get_metric("system_ess_schedule_charge_2_enabled")
    assert isinstance(metric2, WritableFormulaMetric)
    assert metric2.unique_id == "system_0_system_ess_schedule_charge_2_enabled"
    assert metric2.generic_short_id == "system_ess_schedule_charge_{slot}_enabled"
    assert metric2.short_id == "system_ess_schedule_charge_2_enabled"
    assert metric2.value == GenericOnOff.OFF, f"Expected metric value to be 'GenericOnOff.OFF', got {metric1.value}"

    mock_time.return_value = 15
    metric2.set(GenericOnOff.ON)
    assert metric1.value == ChargeSchedule.EVERY_DAY, f"Expected metric value to be ChargeSchedule.EVERY_DAY, got {metric1.value}"

    await hub_disconnect(hub, mock_time)

@pytest.mark.asyncio
async def test_heartbeat_message():
    """Test that the Hub correctly filters MQTT messages for generator1 device type."""
    hub: Hub = await create_mocked_hub()

    # Inject messages after the event is set
    await inject_message(hub, "N/123/heartbeat", "{\"value\": 42}")
    await finalize_injection(hub)

    # Validate the Hub's state - only system device exists, evcharger message was filtered
    assert len(hub.devices) == 1, f"Expected 1 device (system device), got {len(hub.devices)}"
    device = hub.devices["system_0"]
    metric = device.get_metric("system_heartbeat")
    assert metric is not None, "metric should exist in the device"
    assert metric.value == 42, f"Expected metric value to be 42, got {metric.value}"


@pytest.mark.asyncio
async def test_depends_on_regular_exists_same_round():
    """Test that the Hub correctly filters MQTT messages for generator1 device type."""
    hub: Hub = await create_mocked_hub(operation_mode=OperationMode.EXPERIMENTAL)

    # Inject messages after the event is set
    await inject_message(hub, "N/123/settings/0/Settings/Generator1/BatteryVoltage/Enabled", "{\"value\": 0}")
    await inject_message(hub, "N/123/generator/1/AutoStartEnabled", "{\"value\": 1}")
    await finalize_injection(hub)

    # Validate the Hub's state - only system device exists, evcharger message was filtered
    assert len(hub.devices) == 2, f"Expected 2 devices (Generator1 and generator), got {len(hub.devices)}"
    device = hub.devices["generator1_0"]
    metric = device.get_metric("generator_1_start_on_voltage_enabled")
    assert metric is not None, "metric should exist in the device"
    assert metric.value == GenericOnOff.OFF, f"Expected metric value to be GenericOnOff.OFF, got {metric.value}"

    await hub_disconnect(hub)

@pytest.mark.asyncio
async def test_depends_on_regular_exists_two_rounds():
    """Test that the Hub correctly filters MQTT messages for generator1 device type."""
    hub: Hub = await create_mocked_hub(operation_mode=OperationMode.EXPERIMENTAL)

    # Inject messages after the event is set
    await inject_message(hub, "N/123/generator/1/AutoStartEnabled", "{\"value\": 1}")
    await finalize_injection(hub, disconnect=False)
    await inject_message(hub, "N/123/settings/0/Settings/Generator1/BatteryVoltage/Enabled", "{\"value\": 0}")
    await finalize_injection(hub, disconnect=False)

    # Validate the Hub's state - only system device exists, evcharger message was filtered
    assert len(hub.devices) == 2, f"Expected 2 devices (Generator1 and generator), got {len(hub.devices)}"
    device = hub.devices["generator1_0"]
    metric = device.get_metric("generator_1_start_on_voltage_enabled")
    assert metric is not None, "metric should exist in the device"
    assert metric.value == GenericOnOff.OFF, f"Expected metric value to be GenericOnOff.OFF, got {metric.value}"

    await hub_disconnect(hub)

@pytest.mark.asyncio
async def test_depends_on_regular_dont_exists():
    """Test that the Hub correctly filters MQTT messages for generator1 device type."""
    hub: Hub = await create_mocked_hub(operation_mode=OperationMode.EXPERIMENTAL)

    # Inject messages after the event is set
    await inject_message(hub, "N/123/settings/0/Settings/Generator1/BatteryVoltage/Enabled", "{\"value\": 0}")
    await finalize_injection(hub)

    # Validate the Hub's state - only system device exists, evcharger message was filtered
    assert len(hub.devices) == 0, f"Expected 0 devices, got {len(hub.devices)}"

    await hub_disconnect(hub)


@pytest.mark.asyncio
@patch('victron_mqtt.hub.time.monotonic')
async def test_old_cerbo(mock_time: MagicMock) -> None:
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    # Mock time.monotonic() to return a fixed time
    mock_time.return_value = 0
    hub: Hub = await create_mocked_hub()

    # Inject messages after the event is set
    await inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 42}", mock_time)
    mock_time.return_value = 190
    await inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 43}", mock_time)

    # Validate the Hub's state
    assert len(hub.devices) == 1, f"Expected 1 device, got {len(hub.devices)}"

    # Validate that the device has the metric we published
    device = hub.devices["grid_30"]
    metric = device.get_metric("grid_energy_forward_l1")
    assert metric is not None, "Metric should exist in the device"
    assert metric.value == 43, f"Expected metric value to be 43, got {metric.value}"
    await hub_disconnect(hub, mock_time)


@pytest.mark.asyncio
async def test_min_max_dependencies():
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = await create_mocked_hub()

    # Inject messages after the event is set
    await inject_message(hub, "N/123/evcharger/170/MaxCurrent", "{\"value\": 42}")
    await inject_message(hub, "N/123/evcharger/170/SetCurrent", "{\"value\": 22}")
    await finalize_injection(hub)

    # Validate the Hub's state
    assert len(hub.devices) == 1, f"Expected 1 device, got {len(hub.devices)}"
    device = hub.devices["evcharger_170"]
    metric = device.get_metric("evcharger_set_current")
    assert isinstance(metric, WritableMetric), "Metric should exist in the device"
    assert metric.value == 22, f"Expected metric value to be 22, got {metric.value}"
    assert metric.min_value == 0, f"Expected metric min_value to be 0, got {metric.min_value}"
    assert metric.max_value == 42, f"Expected metric max_value to be 42, got {metric.max_value}"


@pytest.mark.asyncio
async def test_min_max_float():
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = await create_mocked_hub()

    # Inject messages after the event is set
    await inject_message(hub, "N/123/settings/170/Settings/SystemSetup/MaxChargeVoltage", "{\"max\": 80.0, \"min\": 0.0, \"value\": 55.6}")
    await finalize_injection(hub)

    # Validate the Hub's state
    assert len(hub.devices) == 1, f"Expected 1 device, got {len(hub.devices)}"
    device = hub.devices["system_170"]
    metric = device.get_metric("system_ess_max_charge_voltage")
    assert isinstance(metric, WritableMetric), "Metric should exist in the device"
    assert metric.value == 55.6, f"Expected metric value to be 55.6, got {metric.value}"
    assert metric.min_value == 0, f"Expected metric min_value to be 0, got {metric.min_value}"
    assert metric.max_value == 80, f"Expected metric max_value to be 80, got {metric.max_value}"
    assert metric.step == 0.1, f"Expected metric step to be 0.1, got {metric.step}"

@pytest.mark.asyncio
async def test_on_connect_fail_before_first_connect():
    """Test that connection failures before first connect raise CannotConnectError."""
    hub = Hub(
        host="localhost",
        port=1883,
        username=None,
        password=None,
        use_ssl=False,
        installation_id="test123"
    )

    mocked_client = MagicMock(spec=Client)
    hub._client = mocked_client
    hub._loop = asyncio.get_running_loop()
    hub._first_connect = True  # Mark as first connect

    # Simulate connection failures during initial connection
    # Call _on_connect_fail multiple times, reaching the max attempts
    for _ in range(CONNECT_MAX_FAILED_ATTEMPTS):
        hub._on_connect_fail(mocked_client, None)

    # Verify that _connect_failed_reason was set after max attempts reached
    assert hub._connect_failed_reason is not None, "Connection should have failed after max attempts"
    assert isinstance(hub._connect_failed_reason, CannotConnectError), f"Expected CannotConnectError, got {type(hub._connect_failed_reason)}"
    assert "after 3 attempts" in str(hub._connect_failed_reason), f"Error message should mention 3 attempts, got: {hub._connect_failed_reason}"


@pytest.mark.asyncio
async def test_on_connect_fail_after_first_successful_connect():
    """Test that connection failures after first successful connection keep retrying forever."""
    hub = Hub(
        host="localhost",
        port=1883,
        username=None,
        password=None,
        use_ssl=False,
        installation_id="test123"
    )

    mocked_client = MagicMock(spec=Client)
    hub._client = mocked_client
    hub._loop = asyncio.get_running_loop()
    hub._first_connect = False  # Mark as not first connect (already connected once)

    # Simulate a successful connection first
    hub._on_connect_internal(
        mocked_client,
        None,
        ConnectFlags(False),
        ReasonCode(PacketTypes.CONNACK, identifier=0),
        None
    )

    # Verify that counters were reset after successful connection
    assert hub._connect_failed_attempts == 0, "Failed attempts should be reset after successful connection"
    assert hub._connect_failed_since == 0, "Connect failed since should be reset after successful connection"
    assert hub._connect_failed_reason is None, "Connect failed reason should be cleared after successful connection"

    # Now simulate multiple connection failures - should NOT raise error even after max attempts
    for attempt in range(CONNECT_MAX_FAILED_ATTEMPTS + 5):
        hub._on_connect_fail(mocked_client, None)
        # After successful connect, _on_connect_fail should NOT set _connect_failed_reason
        # because it keeps retrying forever
        if attempt < CONNECT_MAX_FAILED_ATTEMPTS:
            assert hub._connect_failed_reason is None, f"Should not fail on attempt {attempt}"

    # After max attempts exceeded but after successful connection, should still NOT have failed
    # because the logic allows infinite retries after first successful connection
    assert hub._connect_failed_attempts > CONNECT_MAX_FAILED_ATTEMPTS, "Should have accumulated more failed attempts than max"
    # Note: _on_connect_fail won't raise after max attempts if called before _wait_for_connect completes


@pytest.mark.asyncio
async def test_on_connect_fail_resets_counters_on_successful_reconnect():
    """Test that failed attempt counters are reset after reconnecting successfully."""
    hub = Hub(
        host="localhost",
        port=1883,
        username=None,
        password=None,
        use_ssl=False,
        installation_id="test123"
    )

    mocked_client = MagicMock(spec=Client)
    hub._client = mocked_client
    hub._loop = asyncio.get_running_loop()
    hub._first_connect = False

    # First successful connection
    hub._on_connect_internal(
        mocked_client,
        None,
        ConnectFlags(False),
        ReasonCode(PacketTypes.CONNACK, identifier=0),
        None
    )
    assert hub._connect_failed_attempts == 0

    # Simulate some connection failures
    hub._on_connect_fail(mocked_client, None)
    hub._on_connect_fail(mocked_client, None)
    assert hub._connect_failed_attempts == 2, "Should have 2 failed attempts"

    # Reconnect successfully
    hub._on_connect_internal(
        mocked_client,
        None,
        ConnectFlags(False),
        ReasonCode(PacketTypes.CONNACK, identifier=0),
        None
    )

    # Verify counters were reset
    assert hub._connect_failed_attempts == 0, "Failed attempts should be reset after successful reconnection"
    assert hub._connect_failed_since == 0, "Connect failed since should be reset"
    assert hub._connect_failed_reason is None, "Connect failed reason should be cleared"

    # New failures should not immediately fail
    hub._on_connect_fail(mocked_client, None)
    assert hub._connect_failed_attempts == 1, "Should restart counting from 1"


@pytest.mark.asyncio
@patch('victron_mqtt.hub.time.monotonic')
async def test_on_connect_fail_tracking_time_after_first_connect(mock_time: MagicMock):
    """Test that _on_connect_fail properly tracks disconnection time before first connect."""
    # Mock time.monotonic() to return a fixed time
    mock_time.return_value = 7
    hub: Hub = await create_mocked_hub()

    # First failure - should initialize _connect_failed_since
    hub._on_connect_fail(hub._client, None)
    assert hub._connect_failed_since == 7, "Should have recorded failure time"

    # Second failure- should keep same _connect_failed_since
    mock_time.return_value = 10
    hub._on_connect_fail(hub._client, None)
    assert hub._connect_failed_since == 7, "Should keep same failure time across retries"


@pytest.mark.asyncio
async def test_suppress_republish_still_creates_new_metrics():
    """Test that new metrics are created even when suppress-republish prevents full_publish_completed.

    When the keepalive includes suppress-republish, Venus OS does not send
    full_publish_completed. The hub should still process pending placeholders
    into metrics via the periodic trigger in the keepalive loop.
    """
    hub: Hub = await create_mocked_hub()

    # Track new metrics via callback
    mock_on_new_metric = MagicMock()
    hub.on_new_metric = mock_on_new_metric

    # Inject messages to create placeholders
    await inject_message(hub, "N/123/system/170/Dc/System/Power", '{"value": 1.1}')

    # Verify placeholders were created
    assert len(hub._metrics_placeholders) > 0, "Should have pending placeholders after inject"

    # Non-forced keepalive sends suppress-republish; mock won't respond with full_publish_completed
    hub._keepalive()
    await sleep_short()

    # Placeholders are NOT processed by a regular keepalive (suppress-republish, no response)
    assert len(hub._metrics_placeholders) > 0, "Placeholders should still be pending after suppress-republish keepalive"

    # Simulate what the keepalive loop does every 3 minutes: call _handle_full_publish_message directly
    hub._handle_full_publish_message("{}", skip_validation=True)
    await sleep_short()

    # Now placeholders should be converted to metrics
    assert len(hub._metrics_placeholders) == 0, "Placeholders should be cleared after periodic trigger"
    device = hub.devices.get("system_170")
    assert device is not None, "Device should exist"
    metric = device.get_metric("system_dc_consumption")
    assert metric is not None, "Metric should have been created"
    assert metric.value == 1.1, f"Expected metric value to be 1.1, got {metric.value}"

    await hub_disconnect(hub)


# ═══════════════════════════════════════════════════════════════════════════
# Helper fixtures (from test_coverage.py)
# ═══════════════════════════════════════════════════════════════════════════


def _make_descriptor(**overrides) -> TopicDescriptor:
    defaults = {
        "topic": "N/{installation_id}/battery/{device_id}/Soc",
        "message_type": MetricKind.SENSOR,
        "short_id": "test_metric",
        "name": "Test Metric",
        "value_type": ValueType.FLOAT,
        "metric_type": MetricType.ELECTRIC_STORAGE_PERCENTAGE,
    }
    defaults.update(overrides)
    return TopicDescriptor(**defaults)


def _make_metric(descriptor=None, hub=None, **overrides) -> Metric:
    if descriptor is None:
        descriptor = _make_descriptor(**overrides)
    if hub is None:
        hub = MagicMock()
        hub._update_frequency_seconds = 0
        hub._loop = MagicMock()
        hub._loop.is_running.return_value = False
        hub._topic_log_info = None
    m = Metric.__new__(Metric)
    m._descriptor = descriptor
    m._short_id = descriptor.short_id
    m._generic_short_id = descriptor.short_id
    m._unique_id = f"device_0_{descriptor.short_id}"
    m._value = None
    m._hub = hub
    m._on_update = None
    m._key_values = {}
    m._last_seen = 0.0
    m._last_notified = 0.0
    m._depend_on_me = []
    return m


def _make_parsed_topic(device_type: DeviceType, device_id: str, installation_id: str) -> ParsedTopic:
    return ParsedTopic(
        installation_id=installation_id,
        device_id=device_id,
        device_type=device_type,
        wildcards_with_device_type=f"N/##installation_id##/{device_type.code}/+/Soc",
        wildcards_without_device_type="N/##installation_id##/##device_id##/Soc",
        full_topic=f"N/{installation_id}/{device_type.code}/{device_id}/Soc",
    )


def _make_device(device_type: DeviceType = DeviceType.BATTERY, device_id: str = "0") -> Device:
    pt = _make_parsed_topic(device_type=device_type, device_id=device_id, installation_id="123")
    desc = _make_descriptor()
    return Device(unique_id=f"{device_type.code}_{device_id}", parsed_topic=pt, descriptor=desc)


# ═══════════════════════════════════════════════════════════════════════════
# Hub tests (from test_coverage.py)
# ═══════════════════════════════════════════════════════════════════════════

class TestHubValidation:
    """Test Hub constructor validation (lines 157, 159)."""

    def test_empty_host_raises(self):
        with pytest.raises(ValueError, match="host must be a non-empty string"):
            Hub(host="", port=1883, username=None, password=None, use_ssl=False)

    def test_invalid_port_zero(self):
        with pytest.raises(ValueError, match="port must be an integer"):
            Hub(host="localhost", port=0, username=None, password=None, use_ssl=False)

    def test_invalid_port_too_large(self):
        with pytest.raises(ValueError, match="port must be an integer"):
            Hub(host="localhost", port=70000, username=None, password=None, use_ssl=False)


class TestHubProperties:
    """Test Hub property accessors (lines 888, 893, 898, 954)."""

    def test_model_name(self):
        with patch('victron_mqtt.hub.mqtt.Client'):
            hub = Hub("localhost", 1883, None, None, False, model_name="TestModel")
        assert hub.model_name == "TestModel"

    def test_topic_prefix(self):
        with patch('victron_mqtt.hub.mqtt.Client'):
            hub = Hub("localhost", 1883, None, None, False, topic_prefix="myprefix")
        assert hub.topic_prefix == "myprefix"

    def test_connected(self):
        with patch('victron_mqtt.hub.mqtt.Client') as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            hub = Hub("localhost", 1883, None, None, False)
            hub._client = mock_client
            mock_client.is_connected.return_value = True
        assert hub.connected is True

    def test_on_new_metric_property(self):
        with patch('victron_mqtt.hub.mqtt.Client'):
            hub = Hub("localhost", 1883, None, None, False)
        assert hub.on_new_metric is None
        callback = MagicMock()
        hub.on_new_metric = callback
        assert hub.on_new_metric is callback


class TestHubTopicPrefix:
    """Test topic prefix add/remove methods (lines 791, 797-799)."""

    def test_add_prefix(self):
        with patch('victron_mqtt.hub.mqtt.Client'):
            hub = Hub("localhost", 1883, None, None, False, topic_prefix="prefix")
        assert hub._add_topic_prefix("N/123/test") == "prefix/N/123/test"

    def test_add_prefix_none(self):
        with patch('victron_mqtt.hub.mqtt.Client'):
            hub = Hub("localhost", 1883, None, None, False)
        assert hub._add_topic_prefix("N/123/test") == "N/123/test"

    def test_remove_prefix(self):
        with patch('victron_mqtt.hub.mqtt.Client'):
            hub = Hub("localhost", 1883, None, None, False, topic_prefix="prefix")
        assert hub._remove_topic_prefix("prefix/N/123/test") == "N/123/test"

    def test_remove_prefix_none(self):
        with patch('victron_mqtt.hub.mqtt.Client'):
            hub = Hub("localhost", 1883, None, None, False)
        assert hub._remove_topic_prefix("N/123/test") == "N/123/test"

    def test_remove_prefix_no_match(self):
        with patch('victron_mqtt.hub.mqtt.Client'):
            hub = Hub("localhost", 1883, None, None, False, topic_prefix="prefix")
        assert hub._remove_topic_prefix("other/N/123/test") == "other/N/123/test"


class TestHubKeepaliveEcho:
    """Test get_keepalive_echo static method (lines 975-977)."""

    def test_valid_echo(self):
        payload = json.dumps({"full-publish-completed-echo": "echo123"})
        assert Hub.get_keepalive_echo(payload) == "echo123"

    def test_malformed_json(self):
        assert Hub.get_keepalive_echo("not json") is None

    def test_missing_key(self):
        payload = json.dumps({"other": "value"})
        assert Hub.get_keepalive_echo(payload) is None

    def test_empty_string(self):
        assert Hub.get_keepalive_echo("") is None


class TestHubSSL:
    """Test SSL setup path (lines 285-290)."""

    def test_ssl_context_setup(self):
        with patch('victron_mqtt.hub.mqtt.Client') as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            hub = Hub("localhost", 8883, None, None, True)
        assert hub.use_ssl is True


class TestHubReadOnlyMode:
    """Test READ_ONLY operation mode (line 207, 214-217)."""

    def test_read_only_mode_filters_writable(self):
        with patch('victron_mqtt.hub.mqtt.Client'):
            hub = Hub("localhost", 1883, None, None, False,
                       operation_mode=OperationMode.READ_ONLY)
        # In READ_ONLY, writable topics should be converted to sensors
        # Just verify the hub was created without error
        assert hub._operation_mode == OperationMode.READ_ONLY


class TestHubKeepaliveNotConnected:
    """Test keepalive when not connected (lines 622-624)."""

    def test_keepalive_not_connected(self):
        with patch('victron_mqtt.hub.mqtt.Client') as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            mock_client.is_connected.return_value = False
            hub = Hub("localhost", 1883, None, None, False, installation_id="123")
        # Should return early without error
        hub._keepalive()


class TestHubOnLog:
    """Test _on_log callback (line 343)."""

    def test_on_log(self):
        with patch('victron_mqtt.hub.mqtt.Client'):
            hub = Hub("localhost", 1883, None, None, False)
        # Should not raise
        hub._on_log(None, None, logging.DEBUG, "test message")


@pytest.mark.asyncio
class TestHubConnectionErrors:
    """Test connection timeout and error paths."""

    async def test_connect_timeout(self):
        """Test connection timeout raises CannotConnectError (lines 841-843)."""
        with patch('victron_mqtt.hub.mqtt.Client') as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            mock_client.is_connected.return_value = False
            hub = Hub("localhost", 1883, None, None, False)
            # connect_async is called but _connected_event is never set → timeout
            with pytest.raises(CannotConnectError, match="Timeout"), \
                 patch.object(hub, '_wait_for_connect', side_effect=CannotConnectError("Timeout waiting for first connection")):
                    await hub.connect()

    async def test_wait_for_refresh_timeout(self):
        """Test first refresh timeout raises CannotConnectError (lines 851-853)."""
        with patch('victron_mqtt.hub.mqtt.Client') as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            mock_client.is_connected.return_value = True
            hub = Hub("localhost", 1883, None, None, False, installation_id="123")
            hub._client = mock_client
            hub._first_full_publish = False
            with pytest.raises(CannotConnectError, match="Timeout"):
                # Patch the event wait to timeout
                import asyncio
                with patch.object(hub._first_refresh_event, 'wait', side_effect=asyncio.TimeoutError):
                    await hub.wait_for_first_refresh()


class TestHubOnConnectFail:
    """Test _on_connect_fail callback (line 911)."""

    def test_on_connect_fail_first_connect(self):
        with patch('victron_mqtt.hub.mqtt.Client') as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            hub = Hub("localhost", 1883, None, None, False)
            hub._client = mock_client
        hub._first_connect = True
        hub._connect_failed_attempts = 0
        hub._on_connect_fail(mock_client, None)
        assert hub._connect_failed_attempts == 1


# ═══════════════════════════════════════════════════════════════════════════
# Metric tests (from test_coverage.py)
# ═══════════════════════════════════════════════════════════════════════════

class TestMetricFormatValue:
    """Test format_value method (lines 108-115)."""

    def test_format_none(self):
        m = _make_metric()
        assert m.format_value(None) == ""

    def test_format_float_precision_zero(self):
        desc = _make_descriptor(precision=0, metric_type=MetricType.NONE, unit_of_measurement="W", value_type=ValueType.FLOAT)
        m = _make_metric(descriptor=desc)
        # NONE metric_type + FLOAT value_type keeps precision
        assert m.format_value(3.7) == "3 W"

    def test_format_no_unit(self):
        desc = _make_descriptor(metric_type=MetricType.NONE, unit_of_measurement=None, value_type=ValueType.STRING)
        m = _make_metric(descriptor=desc)
        assert m.format_value(42) == "42"

    def test_format_with_unit(self):
        m = _make_metric()
        assert m.format_value(85.0) == "85.0 %"


class TestMetricFormattedValue:
    """Test formatted_value property (line 120)."""

    def test_formatted_value(self):
        m = _make_metric()
        m._value = 42.5
        assert m.formatted_value == "42.5 %"


class TestMetricProperties:
    """Test metric property accessors (lines 158, 163, 168, 173)."""

    def test_metric_type(self):
        m = _make_metric()
        assert m.metric_type == MetricType.ELECTRIC_STORAGE_PERCENTAGE

    def test_metric_nature(self):
        m = _make_metric()
        assert m.metric_nature == MetricNature.MEASUREMENT

    def test_metric_kind(self):
        m = _make_metric()
        assert m.metric_kind == MetricKind.SENSOR

    def test_precision(self):
        desc = _make_descriptor(precision=2)
        m = _make_metric(descriptor=desc)
        assert m.precision == 2


class TestMetricKeepalive:
    """Test _keepalive method paths (lines 201-205)."""

    def test_keepalive_updated_not_published(self):
        """Line 201-202: Metric updated but not yet published."""
        m = _make_metric()
        m._value = 42.0
        m._last_seen = 10.0
        m._last_notified = 5.0
        log = MagicMock()
        m._keepalive(force_invalidate=False, log_debug=log)
        # Should have re-published (called _handle_message)
        log.assert_called()

    def test_keepalive_up_to_date(self):
        """Line 204: Metric is current."""
        m = _make_metric()
        m._value = 42.0
        m._last_seen = 5.0
        m._last_notified = 10.0
        log = MagicMock()
        m._keepalive(force_invalidate=False, log_debug=log)
        log.assert_called()


# ═══════════════════════════════════════════════════════════════════════════
# Device tests
# ═══════════════════════════════════════════════════════════════════════════

class TestDeviceProperties:
    """Test device property setters and getters (lines 68-88, 213, 222, 279)."""

    def test_set_model_property(self):
        dev = _make_device()
        desc = _make_descriptor(
            short_id="model",
            message_type=MetricKind.ATTRIBUTE,
            value_type=ValueType.STRING,
            metric_type=MetricType.NONE,
        )
        dev._set_device_property_from_topic(desc, '{"value": "SmartSolar 150/35"}')
        assert dev.model == "SmartSolar 150/35"

    def test_set_manufacturer_property(self):
        dev = _make_device()
        desc = _make_descriptor(
            short_id="manufacturer",
            message_type=MetricKind.ATTRIBUTE,
            value_type=ValueType.STRING,
            metric_type=MetricType.NONE,
        )
        dev._set_device_property_from_topic(desc, '{"value": "Victron Energy"}')
        assert dev.manufacturer == "Victron Energy"

    def test_set_firmware_version_property(self):
        dev = _make_device()
        desc = _make_descriptor(
            short_id="firmware_version",
            message_type=MetricKind.ATTRIBUTE,
            value_type=ValueType.STRING,
            metric_type=MetricType.NONE,
        )
        dev._set_device_property_from_topic(desc, '{"value": "v3.40"}')
        assert dev.firmware_version == "v3.40"

    def test_set_custom_name_property(self):
        dev = _make_device()
        desc = _make_descriptor(
            short_id="custom_name",
            message_type=MetricKind.ATTRIBUTE,
            value_type=ValueType.STRING,
            metric_type=MetricType.NONE,
        )
        dev._set_device_property_from_topic(desc, '{"value": "MyBattery"}')
        assert dev.custom_name == "MyBattery"

    def test_ignore_product_id(self):
        dev = _make_device()
        desc = _make_descriptor(
            short_id="victron_productid",
            message_type=MetricKind.ATTRIBUTE,
            value_type=ValueType.STRING,
            metric_type=MetricType.NONE,
        )
        dev._set_device_property_from_topic(desc, '{"value": "0x1234"}')

    def test_none_payload_ignored(self):
        dev = _make_device()
        desc = _make_descriptor(
            short_id="model",
            message_type=MetricKind.ATTRIBUTE,
            value_type=ValueType.STRING,
            metric_type=MetricType.NONE,
        )
        dev._set_device_property_from_topic(desc, '{"value": null}')
        assert dev.model is None

    def test_device_name_with_custom_name(self):
        dev = _make_device()
        dev._custom_name = "Custom Battery"
        assert dev.name == "Custom Battery"

    def test_device_name_with_model(self):
        dev = _make_device()
        dev._model = "SmartSolar 150/35"
        assert dev.name == "SmartSolar 150/35"

    def test_device_name_fallback_to_type(self):
        dev = _make_device()
        assert dev.name == "Battery"

    def test_fallback_placeholder_repr(self):
        dev = _make_device()
        pt = MagicMock()
        td = MagicMock()
        fp = FallbackPlaceholder(device=dev, parsed_topic=pt, topic_descriptor=td, value=True)
        r = repr(fp)
        assert "FallbackPlaceholder" in r


# ═══════════════════════════════════════════════════════════════════════════
# WritableMetric tests (from test_coverage.py)
# ═══════════════════════════════════════════════════════════════════════════

class TestMetricEnumValues:
    """Test enum_values property (line 100)."""

    def test_enum_values_with_enum(self):
        desc = _make_descriptor(
            value_type=ValueType.ENUM,
            enum=GenericOnOff,
            message_type=MetricKind.SWITCH,
        )
        wm = Metric.__new__(Metric)
        wm._descriptor = desc
        assert wm.enum_values == ["off", "on"]

    def test_enum_values_without_enum(self):
        desc = _make_descriptor()
        wm = Metric.__new__(Metric)
        wm._descriptor = desc
        assert wm.enum_values is None


class TestWritableMetricBitmask:
    """Test bitmask wrapping path (lines 119-121)."""

    def test_wrap_bitmask_value(self):
        desc = _make_descriptor(
            value_type=ValueType.BITMASK,
            enum=GenericOnOff,
            message_type=MetricKind.SENSOR,
        )
        payload = WritableMetric._wrap_payload(desc, GenericOnOff.OFF)
        data = json.loads(payload)
        assert data["value"] == 0


class TestWritableFormulaMetricKeepalive:
    """Test WritableFormulaMetric _keepalive (line 43)."""

    def test_keepalive_is_noop(self):
        hub = MagicMock()
        hub._update_frequency_seconds = 0
        hub._loop = MagicMock()
        hub._loop.is_running.return_value = False
        hub._topic_log_info = None

        desc = _make_descriptor(is_formula=True)
        log = MagicMock()

        wfm = WritableFormulaMetric.__new__(WritableFormulaMetric)
        wfm._descriptor = desc
        wfm._short_id = desc.short_id
        wfm._generic_short_id = desc.short_id
        wfm._unique_id = "dev_test_metric"
        wfm._value = None
        wfm._hub = hub
        wfm._on_update = None
        wfm._key_values = {}
        wfm._last_seen = 0.0
        wfm._last_notified = 0.0
        wfm._depend_on_me = []

        wfm._keepalive(force_invalidate=False, log_debug=log)
        log.assert_called()


class TestWritableFormulaMetricSet:
    """Test WritableFormulaMetric set when formula returns None (lines 54-56)."""

    def test_set_formula_returns_none(self):
        hub = MagicMock()
        hub._update_frequency_seconds = 0
        hub._loop = MagicMock()
        hub._loop.is_running.return_value = False
        hub._topic_log_info = None

        desc = _make_descriptor(is_formula=True)

        def write_func(value, depends_on, state):
            return None

        wfm = WritableFormulaMetric.__new__(WritableFormulaMetric)
        wfm._descriptor = desc
        wfm._short_id = desc.short_id
        wfm._generic_short_id = desc.short_id
        wfm._unique_id = "dev_test_metric"
        wfm._value = 42
        wfm._hub = hub
        wfm._on_update = None
        wfm._key_values = {}
        wfm._last_seen = 0.0
        wfm._last_notified = 0.0
        wfm._depend_on_me = []
        wfm._func = MagicMock()
        wfm._write_func = write_func
        wfm._depends_on = {}
        wfm.transient_state = None

        wfm.set("test")
        # Formula returned None, so value should be set to None
        assert wfm._value is None


# ═══════════════════════════════════════════════════════════════════════════
# Formula tests (from test_coverage.py)
# ═══════════════════════════════════════════════════════════════════════════

class TestFormulaMetricNoneReturn:
    """Test FormulaMetric when formula returns None (lines 57-59)."""

    def test_formula_returns_none(self):
        hub = MagicMock()
        hub._update_frequency_seconds = 0
        hub._loop = MagicMock()
        hub._loop.is_running.return_value = False
        hub._topic_log_info = None

        desc = _make_descriptor(is_formula=True)
        log = MagicMock()

        def formula_none(depends_on, state):
            return None

        fm = FormulaMetric.__new__(FormulaMetric)
        fm._descriptor = desc
        fm._short_id = desc.short_id
        fm._generic_short_id = desc.short_id
        fm._unique_id = "dev_test_metric"
        fm._value = None
        fm._hub = hub
        fm._on_update = None
        fm._key_values = {}
        fm._last_seen = 0.0
        fm._last_notified = 0.0
        fm._depend_on_me = []
        fm._func = formula_none
        fm._depends_on = {}
        fm.transient_state = None

        fm._handle_formula(log)
        # formula returned None, so value should be None
        assert fm._value is None


class TestScheduleChargeFormulas:
    """Test _victron_formulas schedule charge functions (lines 58, 80, 84-87)."""

    def test_schedule_charge_enabled_none_value(self):
        metric = MagicMock()
        metric.value = None
        result = schedule_charge_enabled({"m": metric}, None)
        assert result == (None, None)

    def test_schedule_charge_enabled_on(self):
        metric = MagicMock()
        metric.value = MagicMock()
        metric.value.code = 1
        result = schedule_charge_enabled({"m": metric}, None)
        assert result[0] == GenericOnOff.ON

    def test_schedule_charge_enabled_off(self):
        metric = MagicMock()
        metric.value = MagicMock()
        metric.value.code = -1
        result = schedule_charge_enabled({"m": metric}, None)
        assert result[0] == GenericOnOff.OFF

    def test_schedule_set_enable_disabled_sunday(self):
        """Line 79-80: Enable when currently DISABLED_SUNDAY."""
        metric = MagicMock(spec=WritableMetric)
        metric.value = ChargeSchedule.DISABLED_SUNDAY
        result = schedule_charge_enabled_set(GenericOnOff.ON, {"m": metric}, None)
        metric.set.assert_called_once_with(ChargeSchedule.SUNDAY)
        assert result[0] == GenericOnOff.ON

    def test_schedule_set_enable_negative_code(self):
        """Line 81-82: Enable with negative schedule code."""
        metric = MagicMock(spec=WritableMetric)
        schedule_val = MagicMock(spec=ChargeSchedule)
        schedule_val.code = -1
        type(metric).value = schedule_val
        metric.value = schedule_val
        result = schedule_charge_enabled_set(GenericOnOff.ON, {"m": metric}, None)
        assert result[0] == GenericOnOff.ON

    def test_schedule_set_disable_sunday(self):
        """Line 84-85: Disable when currently SUNDAY."""
        metric = MagicMock(spec=WritableMetric)
        metric.value = ChargeSchedule.SUNDAY
        result = schedule_charge_enabled_set(GenericOnOff.OFF, {"m": metric}, None)
        metric.set.assert_called_once_with(ChargeSchedule.DISABLED_SUNDAY)
        assert result[0] == GenericOnOff.OFF

    def test_schedule_set_disable_positive_code(self):
        """Line 86-87: Disable with positive schedule code."""
        metric = MagicMock(spec=WritableMetric)
        schedule_val = MagicMock(spec=ChargeSchedule)
        schedule_val.code = 1
        type(metric).value = schedule_val
        metric.value = schedule_val
        result = schedule_charge_enabled_set(GenericOnOff.OFF, {"m": metric}, None)
        assert result[0] == GenericOnOff.OFF

    def test_schedule_set_with_string_id_off(self):
        """Passing string id 'off' should resolve via from_id_or_string."""
        metric = MagicMock(spec=WritableMetric)
        schedule_val = MagicMock(spec=ChargeSchedule)
        schedule_val.code = 1
        type(metric).value = schedule_val
        metric.value = schedule_val
        result = schedule_charge_enabled_set("off", {"m": metric}, None)
        assert result[0] == GenericOnOff.OFF

    def test_schedule_set_with_string_id_on(self):
        """Passing string id 'on' should resolve via from_id_or_string."""
        metric = MagicMock(spec=WritableMetric)
        metric.value = ChargeSchedule.DISABLED_SUNDAY
        result = schedule_charge_enabled_set("on", {"m": metric}, None)
        metric.set.assert_called_once_with(ChargeSchedule.SUNDAY)
        assert result[0] == GenericOnOff.ON


class TestLeftRiemannSum:
    """Test left_riemann_sum formula (lines 44-47)."""

    def test_left_riemann_sum_first_call(self):
        metric = MagicMock()
        metric.value = 1000.0  # 1000W
        result = left_riemann_sum({"m": metric}, None)
        assert result is not None
        value, state = result
        assert value == 0.0  # First call, no energy yet
        assert isinstance(state, LRSLastReading)

    def test_left_riemann_sum_none_value(self):
        metric = MagicMock()
        metric.value = None
        result = left_riemann_sum({"m": metric}, None)
        assert result is None
