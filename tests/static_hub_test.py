import asyncio
import pytest
from unittest.mock import MagicMock, patch
from paho.mqtt.client import ConnectFlags
from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.reasoncodes import ReasonCode
from victron_mqtt._victron_enums import ChargeSchedule, DeviceType, GenericOnOff
from victron_mqtt.hub import Hub, TopicNotFoundError
from victron_mqtt.constants import OperationMode
from victron_mqtt.metric import Metric
from victron_mqtt.writable_formula_metric import WritableFormulaMetric
from victron_mqtt.writable_metric import WritableMetric
from victron_mqtt._victron_topics import topics
from victron_mqtt.testing import (
    create_mocked_hub,
    inject_message,
    finalize_injection,
    sleep_short,
    hub_disconnect,
)
import logging

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
    from victron_mqtt.hub import AuthenticationError
    
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
        def mock_connect_async_auth_fail(*args, **kwargs):
            if hub._client is not None:
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
    metric = device.get_metric("grid_energy_forward_L1")
    metric2 = hub.get_metric("grid_30_grid_energy_forward_L1")
    assert metric == metric2, "Metrics should be equal"
    assert metric is not None, "Metric should exist in the device"
    assert metric.value == 42, f"Expected metric value to be 42, got {metric.value}"
    assert metric.short_id == "grid_energy_forward_L1", f"Expected metric short_id to be 'grid_energy_forward_L1', got {metric.short_id}"
    assert metric.generic_short_id == "grid_energy_forward_{phase}", f"Expected metric generic_short_id to be 'grid_energy_forward_{{phase}}', got {metric.generic_short_id}"
    assert metric.unique_id == "grid_30_grid_energy_forward_L1", f"Expected metric unique_id to be 'grid_30_grid_energy_forward_L1', got {metric.unique_id}"
    assert metric.name == "Grid consumption on L1", f"Expected metric name to be 'Grid consumption on L1', got {metric.name}"
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
    assert metric.value == GenericOnOff.On, f"Expected metric value to be GenericOnOff.On, got {metric.value}"
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
    device = list(hub.devices.values())[0]
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
    def mock__publish(topic, value):
        published['topic'] = topic
        published['value'] = value
        # Call the original publish if needed
        if hasattr(hub._publish, '__wrapped__'):
            return hub._publish.__wrapped__(topic, value) # type: ignore
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

def test_expend_topics():
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
    assert metric.value == GenericOnOff.On, f"Expected metric value to be GenericOnOff.On, got {metric.value}"

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
    assert metric.generic_name == "Battery cell {cell_id} voltage", f"Expected metric generic_name to be 'Battery cell {{cell_id}} voltage', got {metric.generic_name}"

@pytest.mark.asyncio
async def test_same_message_events_none():
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = await create_mocked_hub()

    # Inject messages after the event is set
    await inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 42}")
    await finalize_injection(hub, False)

    # Validate that the device has the metric we published
    device = hub.devices["grid_30"]
    metric = device.get_metric("grid_energy_forward_L1")
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
    metric = device.get_metric("grid_energy_forward_L1")
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
async def test_same_message_events_five(mock_time):
    """Test that the Hub correctly updates its internal state based on MQTT messages."""

    mock_time.return_value = 0.0
    hub: Hub = await create_mocked_hub(update_frequency_seconds=5)

    mock_time.return_value = 10

    # Inject messages after the event is set
    await inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 42}", mock_time)
    await finalize_injection(hub, False)

    # Validate that the device has the metric we published
    device = hub.devices["grid_30"]
    metric = device.get_metric("grid_energy_forward_L1")
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
async def test_metric_keepalive_update_frequency_5(mock_time):
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    mock_time.return_value = 0
    hub: Hub = await create_mocked_hub(update_frequency_seconds=5)

    mock_time.return_value = 10

    # Inject messages after the event is set
    await inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 10}", mock_time)
    await finalize_injection(hub, False)

    # Validate that the device has the metric we published
    device = hub.devices["grid_30"]
    metric = device.get_metric("grid_energy_forward_L1")
    assert metric is not None, "Metric should exist in the device"
    assert metric.value == 10, f"Expected metric value to be 10, got {metric.value}"

    def on_metric_update(metric, value):
        logger.debug(f"Update: Metric={repr(metric)}, value={value}")
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

    # Invalidate all metrics, as the silent period is 60 seconds we need to go higher
    mock_time.return_value = 76
    hub._keepalive_metrics()
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
async def test_metric_keepalive_update_frequency_none(mock_time):
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    mock_time.return_value = 0
    hub: Hub = await create_mocked_hub()

    mock_time.return_value = 10

    # Inject messages after the event is set
    await inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 10}", mock_time)
    await finalize_injection(hub, False)

    # Validate that the device has the metric we published
    device = hub.devices["grid_30"]
    metric = device.get_metric("grid_energy_forward_L1")
    assert metric is not None, "Metric should exist in the device"
    assert metric.value == 10, f"Expected metric value to be 10, got {metric.value}"

    def on_metric_update(metric, value):
        logger.debug(f"Update: Metric={repr(metric)}, value={value}")
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

    # Invalidate all metrics, as the silent period is 60 seconds we need to go higher
    mock_time.return_value = 76
    hub._keepalive_metrics()
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
    assert metric.value == GenericOnOff.On, f"Expected metric value to be GenericOnOff.On, got {metric.value}"


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
    assert metric1.value == GenericOnOff.On, f"Expected metric value to be GenericOnOff.On, got {metric1.value}"

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
    assert metric2.value == GenericOnOff.Off, f"Expected metric value to be GenericOnOff.Off, got {metric2.value}"

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
    def on_new_metric_mock(hub, device, metric):
        logger.debug(f"New metric added: Hub={hub}, Device={device}, Metric={repr(metric)}")
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
    await hub._keepalive()
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
async def test_new_metric_duplicate_messages():
    """Test that the Hub correctly triggers the on_new_metric callback."""
    hub: Hub = await create_mocked_hub()

    # Mock the on_new_metric callback
    def on_new_metric_mock(hub, device, metric):
        logger.debug(f"New metric added: Hub={hub}, Device={device}, Metric={repr(metric)}")
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
    await hub._keepalive()
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
    def on_new_metric_mock(hub, device, metric):
        logger.debug(f"New metric added: Hub={hub}, Device={device}, Metric={repr(metric)}")
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
    await hub._keepalive()
    # Wait for the callback to be triggered
    await sleep_short()
    assert mock_on_new_metric.call_count == 3, "on_new_metric should be called exactly 3 times"

    # Inject another message. Should generate this but not the formula metrics again
    await inject_message(hub, "N/123/gps/170/Position/Latitude", "{\"value\": 2.3456}")
    await finalize_injection(hub, disconnect=False)

    # Check that we got the callback only once
    await hub._keepalive()
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
    hub: Hub = await create_mocked_hub(operation_mode=OperationMode.EXPERIMENTAL)
    mocked_client: MagicMock = hub._client # type: ignore

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
    hub: Hub = await create_mocked_hub(operation_mode=OperationMode.EXPERIMENTAL)
    mocked_client: MagicMock = hub._client # type: ignore

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
    assert metric.value == GenericOnOff.On, f"Expected metric value to be 1, got {metric.value}"
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
    assert metric.value == GenericOnOff.On, f"Expected metric value to be 1, got {metric.value}"
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
    assert metric.value == GenericOnOff.On, f"Expected metric value to be 1, got {metric.value}"
    assert metric.key_values["output"] == "bla"

    device = hub.devices["switch_155"]
    assert len(device._metrics) == 2, f"Expected 2 metrics, got {len(device._metrics)}"
    metric = device.get_metric("switch_1_state")
    assert metric is not None, "metric should exist in the device"
    assert metric.name == "Switch foo state", "Expected metric name to be 'Switch foo state', got {metric.name}"
    assert metric.generic_name == "Switch {output} state", "Expected metric name to be 'Switch {output} state', got {metric.name}"
    assert metric.value == GenericOnOff.On, f"Expected metric value to be 1, got {metric.value}"
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
    from paho.mqtt.client import Client
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
    hub: Hub = await create_mocked_hub()

    # Inject messages after the event is set
    await inject_message(hub, "N/123/evcharger/170/SetCurrent", "{\"value\": null}")
    await finalize_injection(hub)

    # Validate the Hub's state - only system device exists, evcharger message was filtered
    assert len(hub.devices) == 0, f"Expected no devices, got {len(hub.devices)}"

@pytest.mark.asyncio
@patch('victron_mqtt.formula_common.time.monotonic')
async def test_formula_metric(mock_time):
    # Mock time.monotonic() to return a fixed time
    mock_time.return_value = 0

    hub: Hub = await create_mocked_hub(operation_mode=OperationMode.EXPERIMENTAL)

    # Inject messages after the event is set
    await inject_message(hub, "N/123/system/0/Dc/Battery/Power", "{\"value\": 1200}", mock_time)
    mock_time.return_value += 0.1
    await finalize_injection(hub, disconnect=False)

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
async def test_formula_switch(mock_time):
    # Mock time.monotonic() to return a fixed time
    mock_time.return_value = 0

    hub: Hub = await create_mocked_hub(operation_mode=OperationMode.EXPERIMENTAL)

    # Inject messages after the event is set
    await inject_message(hub, "N/123/settings/0/Settings/CGwacs/BatteryLife/Schedule/Charge/2/Day", "{\"value\": -7}", mock_time)
    mock_time.return_value += 0.1
    await finalize_injection(hub, disconnect=False)

    # Validate the Hub's state - only system device exists
    assert len(hub.devices) == 1, f"Expected 1 device (system device), got {len(hub.devices)}"
    device = hub.devices["system_0"]
    assert len(device._metrics) == 2, f"Expected 2 metrics, got {len(device._metrics)}"

    metric1 = device.get_metric("system_ess_schedule_charge_2_days")
    assert metric1 is not None, "metric should exist in the device"
    assert metric1.unique_id == "system_0_system_ess_schedule_charge_2_days"
    assert metric1.value == ChargeSchedule.DisabledEveryDay, f"Expected metric value to be -7, got {metric1.value}"

    metric2 = device.get_metric("system_ess_schedule_charge_2_enabled")
    assert isinstance(metric2, WritableFormulaMetric)
    assert metric2.unique_id == "system_0_system_ess_schedule_charge_2_enabled"
    assert metric2.generic_short_id == "system_ess_schedule_charge_{slot}_enabled"
    assert metric2.short_id == "system_ess_schedule_charge_2_enabled"
    assert metric2.value == GenericOnOff.Off, f"Expected metric value to be 'GenericOnOff.Off', got {metric1.value}"

    mock_time.return_value = 15
    metric2.set(GenericOnOff.On)
    assert metric1.value == ChargeSchedule.EveryDay, f"Expected metric value to be ChargeSchedule.EveryDay, got {metric1.value}"

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
    device = hub.devices["Generator1_0"]
    metric = device.get_metric("generator_1_start_on_voltage_enabled")
    assert metric is not None, "metric should exist in the device"
    assert metric.value == GenericOnOff.Off, f"Expected metric value to be GenericOnOff.Off, got {metric.value}"

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
    device = hub.devices["Generator1_0"]
    metric = device.get_metric("generator_1_start_on_voltage_enabled")
    assert metric is not None, "metric should exist in the device"
    assert metric.value == GenericOnOff.Off, f"Expected metric value to be GenericOnOff.Off, got {metric.value}"

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
async def test_old_cerbo(mock_time):
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    # Mock time.monotonic() to return a fixed time
    mock_time.return_value = 0
    hub: Hub = await create_mocked_hub()

    # Inject messages after the event is set
    await inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 42}", mock_time)
    mock_time.return_value = 46
    await inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 43}", mock_time)

    # Validate the Hub's state
    assert len(hub.devices) == 1, f"Expected 1 device, got {len(hub.devices)}"

    # Validate that the device has the metric we published
    device = hub.devices["grid_30"]
    metric = device.get_metric("grid_energy_forward_L1")
    assert metric is not None, "Metric should exist in the device"
    assert metric.value == 43, f"Expected metric value to be 43, got {metric.value}"
    await hub_disconnect(hub, mock_time)


@pytest.mark.asyncio
async def test_min_max_dependencies():
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
