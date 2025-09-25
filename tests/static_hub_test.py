import pytest
import pytest_asyncio
import asyncio
from unittest.mock import MagicMock, patch
from datetime import datetime
from victron_mqtt._victron_enums import DeviceType, GenericOnOff
from victron_mqtt.hub import Hub, TopicNotFoundError
from victron_mqtt.constants import TOPIC_INSTALLATION_ID, OperationMode
from victron_mqtt.metric import Metric
from victron_mqtt.writable_metric import WritableMetric
from victron_mqtt._victron_topics import topics
import json
import logging

# Configure logging for the test
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def create_mocked_hub(installation_id=None, operation_mode: OperationMode = OperationMode.FULL, device_type_exclude_filter: list[DeviceType] | None = None, update_frequency_seconds: int | None = None) -> Hub:
    """Helper function to create and return a mocked Hub object."""
    with patch('victron_mqtt.hub.mqtt.Client') as mock_client:
        hub = Hub(host="localhost", port=1883, username=None, password=None, use_ssl=False, installation_id = installation_id, operation_mode=operation_mode, device_type_exclude_filter=device_type_exclude_filter, update_frequency_seconds=update_frequency_seconds)
        mocked_client = MagicMock()
        mock_client.return_value = mocked_client

        # Set up required mock methods
        mocked_client.subscribe = MagicMock()
        mocked_client.is_connected.return_value = True

        # Set the mocked client explicitly to prevent overwriting
        hub._client = mocked_client

        # Dynamically mock undefined attributes
        setattr(hub, '_process_device', MagicMock(name="_process_device"))
        setattr(hub, '_process_metric', MagicMock(name="_process_metric"))

        # Mock connect_async to trigger the _on_connect callback
        def mock_connect_async(*args, **kwargs):
            if hub._client is not None:
                hub._on_connect(hub._client, None, {}, 0)
        mocked_client.connect_async = MagicMock(name="connect_async", side_effect=mock_connect_async)

        # Ensure loop_start is a no-op
        mocked_client.loop_start = MagicMock(name="loop_start")

        # Mock on_message to handle incoming messages
        mocked_client.on_message = MagicMock(name="on_message")

        # Mock _subscribe to automatically publish a message to TOPIC_INSTALLATION_ID
        def mock_subscribe(topic):
            if topic == TOPIC_INSTALLATION_ID:
                mocked_client.on_message(
                    mocked_client,
                    None,
                    MagicMock(topic="N/123/system/0/Serial", payload=b'{"value": "123"}')
                )
                return
            assert "{installation_id}" not in topic
            assert not topic.startswith("N/+")

        mocked_client.subscribe = MagicMock(name="subscribe", side_effect=mock_subscribe)

        def mock_publish(topic, value):
            if topic == "R/123/keepalive":
                echo = parse_keepalive_options(value)
                keepalive_payload = json.dumps({"full-publish-completed-echo": echo, "value": 42})
                mocked_client.on_message(
                    mocked_client,
                    None,
                    MagicMock(topic="N/123/full_publish_completed", payload=keepalive_payload.encode())
                )
        mocked_client.publish = MagicMock(name="publish", side_effect=mock_publish)

        await hub.connect()

        return hub

def parse_keepalive_options(json_string: str) -> str:
    """Parse the JSON string for keepalive options and return the echo value."""
    try:
        options = json.loads(json_string)
        keepalive_options = options.get("keepalive-options", [])
        if keepalive_options and isinstance(keepalive_options, list):
            return keepalive_options[0].get("full-publish-completed-echo", "")
        return ""
    except (json.JSONDecodeError, AttributeError, IndexError):
        return ""



def inject_message(hub_instance, topic, payload):
    """Helper function to inject a single MQTT message into the Hub."""
    hub_instance._client.on_message(None, None, MagicMock(topic=topic, payload=payload.encode()))

async def finalize_injection(hub: Hub, disconnect: bool = True):
    """Finalize the injection of messages into the Hub."""
    # Wait for the connect task to finish
    await hub._keepalive()
    await hub.wait_for_first_refresh()
    if disconnect:
        await hub.disconnect()

@pytest.mark.asyncio
async def test_hub_initialization():
    """Test that the Hub initializes correctly."""
    hub: Hub = await create_mocked_hub()
    assert hub._client is not None, "MQTT client should be initialized"

@pytest.mark.asyncio
async def test_hub_message_handling():
    """Test that the Hub processes incoming MQTT messages correctly."""
    hub: Hub = await create_mocked_hub()

    # Inject a message
    inject_message(hub, "N/device/123/metric/456", "{\"value\": 42}")

    # Validate the Hub's state
    assert len(hub.devices) == 1, "No devices should be created"

    await finalize_injection(hub)

@pytest.mark.asyncio
async def test_phase_message():
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = await create_mocked_hub()

    # Inject messages after the event is set
    inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 42}")
    await finalize_injection(hub)

    # Validate the Hub's state
    assert len(hub.devices) == 2, f"Expected 2 device, got {len(hub.devices)}"

    # Validate that the device has the metric we published
    device = hub.devices["grid_30"]
    assert device.device_type == DeviceType.GRID, f"Expected metric type to be 'grid', got {device.device_type}"
    assert device.unique_id == "123_grid_30", f"Expected device unique_id to be '123_grid_30', got {device.unique_id}"
    metric = device.get_metric_from_unique_id("123_grid_30_grid_energy_forward_L1")
    metric2 = hub.get_metric_from_unique_id("123_grid_30_grid_energy_forward_L1")
    assert metric == metric2, "Metrics should be equal"
    assert metric is not None, "Metric should exist in the device"
    assert metric.value == 42, f"Expected metric value to be 42, got {metric.value}"
    assert metric.short_id == "grid_energy_forward_L1", f"Expected metric short_id to be 'grid_energy_forward_L1', got {metric.short_id}"
    assert metric.generic_short_id == "grid_energy_forward_{phase}", f"Expected metric generic_short_id to be 'grid_energy_forward_{{phase}}', got {metric.generic_short_id}"
    assert metric.unique_id == "123_grid_30_grid_energy_forward_L1", f"Expected metric unique_id to be '123_grid_30_grid_energy_forward_L1', got {metric.unique_id}"
    assert metric.name == "Grid consumption on L1", f"Expected metric name to be 'Grid consumption on L1', got {metric.name}"
    assert metric.generic_name == "Grid consumption on {phase}", f"Expected metric generic_name to be 'Grid consumption on {{phase}}', got {metric.generic_name}"
    assert metric.unit_of_measurement == "kWh", f"Expected metric unit_of_measurement to be 'kWh', got {metric.unit_of_measurement}"
    assert metric.key_values["phase"] == "L1"


@pytest.mark.asyncio
async def test_placeholder_message():
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = await create_mocked_hub()

    # Inject messages after the event is set
    inject_message(hub, "N/123/system/0/Relay/0/State", "{\"value\": 1}")
    await finalize_injection(hub)

    # Validate the Hub's state
    assert len(hub.devices) == 1, f"Expected 1 device, got {len(hub.devices)}"

    # Validate that the device has the metric we published
    device =hub.devices["system_0"]
    assert device.unique_id == "123_system_0", f"Expected 123_system_0. Got {device.unique_id}"
    metric = device.get_metric_from_unique_id("123_system_0_system_relay_0")
    assert metric is not None, "Metric should exist in the device"
    assert metric.value == GenericOnOff.On, f"Expected metric value to be GenericOnOff.On, got {metric.value}"
    assert metric.name == "Relay 0 state", f"Expected metric name to be 'Relay 0 state', got {metric.name}"
    assert metric.generic_name == "Relay {relay} state", f"Expected metric generic_name to be 'Relay {{relay}} state', got {metric.generic_name}"

@pytest.mark.asyncio
async def test_dynamic_min_max_message():
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = await create_mocked_hub()

    # Inject messages after the event is set
    inject_message(hub, "N/123/settings/0/Settings/CGwacs/AcPowerSetPoint", '{"max": 1000000, "min": -1000000, "value": 50}')
    await finalize_injection(hub)

    # Validate the Hub's state
    assert len(hub.devices) == 1, f"Expected 1 device, got {len(hub.devices)}"

    # Validate that the device has the metric we published
    device = list(hub.devices.values())[0]
    writable_metric = device.get_metric_from_unique_id("123_system_0_system_ac_power_set_point")
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
    inject_message(hub, "N/123/evcharger/170/SetCurrent", "{\"value\": 100}")

    await finalize_injection(hub, False)

    # Validate the Hub's state
    assert len(hub.devices) == 2, f"Expected 2 device, got {len(hub.devices)}"

    # Validate that the device has the metric we published
    device = hub.devices["evcharger_170"]
    writable_metric = device.get_metric_from_unique_id("123_evcharger_170_evcharger_set_current")
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

    await hub.disconnect()


@pytest.mark.asyncio
async def test_placeholder_adjustable_on():
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = await create_mocked_hub()

    # Inject messages after the event is set
    inject_message(hub, "N/123/vebus/170/Ac/ActiveIn/CurrentLimit", "{\"value\": 100}")
    inject_message(hub, "N/123/vebus/170/Ac/ActiveIn/CurrentLimitIsAdjustable", "{\"value\": 1}")
    await finalize_injection(hub)

    # Validate the Hub's state
    assert len(hub.devices) == 2, f"Expected 2 device, got {len(hub.devices)}"

    # Validate that the device has the metric we published
    device = hub.devices["vebus_170"]
    assert len(device._metrics) == 1, f"Expected 1 metrics, got {len(device._metrics)}"
    writable_metric = device.get_metric_from_unique_id("123_vebus_170_vebus_inverter_current_limit")
    assert isinstance(writable_metric, WritableMetric), f"Expected writable_metric to be of type WritableMetric, got {type(writable_metric)}"
    assert writable_metric is not None, "WritableMetric should exist in the device"
    assert writable_metric.value == 100, f"Expected writable_metric value to be 100, got {writable_metric.value}"
    # Ensure cleanup happens even if the test fails

@pytest.mark.asyncio
async def test_placeholder_adjustable_off():
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = await create_mocked_hub()

    # Inject messages after the event is set
    inject_message(hub, "N/123/vebus/170/Ac/ActiveIn/CurrentLimit", "{\"value\": 100}")
    inject_message(hub, "N/123/vebus/170/Ac/ActiveIn/CurrentLimitIsAdjustable", "{\"value\": 0}")
    await finalize_injection(hub)

    # Validate the Hub's state
    assert len(hub.devices) == 2, f"Expected 2 device, got {len(hub.devices)}"

    # Validate that the device has the metric we published
    device = hub.devices["vebus_170"]
    assert len(device._metrics) == 1, f"Expected 1 metrics, got {len(device._metrics)}"
    metric = device.get_metric_from_unique_id("123_vebus_170_vebus_inverter_current_limit")
    assert not isinstance(metric, WritableMetric), f"Expected metric to be of type Metric, got {type(metric)}"
    assert metric is not None, "metric should exist in the device"
    assert metric.value == 100, f"Expected metric value to be 100, got {metric.value}"
    # Ensure cleanup happens even if the test fails

@pytest.mark.asyncio
async def test_placeholder_adjustable_on_reverse():
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = await create_mocked_hub()

    # Inject messages after the event is set
    inject_message(hub, "N/123/vebus/170/Ac/ActiveIn/CurrentLimitIsAdjustable", "{\"value\": 1}")
    inject_message(hub, "N/123/vebus/170/Ac/ActiveIn/CurrentLimit", "{\"value\": 100}")
    await finalize_injection(hub)

    # Validate that the device has the metric we published
    device = hub.devices["vebus_170"]
    assert len(device._metrics) == 1, f"Expected 1 metrics, got {len(device._metrics)}"
    writable_metric = device.get_metric_from_unique_id("123_vebus_170_vebus_inverter_current_limit")
    assert isinstance(writable_metric, WritableMetric), f"Expected writable_metric to be of type WritableMetric, got {type(writable_metric)}"
    assert writable_metric is not None, "WritableMetric should exist in the device"
    assert writable_metric.value == 100, f"Expected writable_metric value to be 100, got {writable_metric.value}"
    # Ensure cleanup happens even if the test fails

@pytest.mark.asyncio
async def test_placeholder_adjustable_off_reverse():
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = await create_mocked_hub()

    # Inject messages after the event is set
    inject_message(hub, "N/123/vebus/170/Ac/ActiveIn/CurrentLimitIsAdjustable", "{\"value\": 0}")
    inject_message(hub, "N/123/vebus/170/Ac/ActiveIn/CurrentLimit", "{\"value\": 100}")
    await finalize_injection(hub)

    # Validate that the device has the metric we published
    device = hub.devices["vebus_170"]
    assert len(device._metrics) == 1, f"Expected 1 metrics, got {len(device._metrics)}"
    writable_metric = device.get_metric_from_unique_id("123_vebus_170_vebus_inverter_current_limit")
    assert not isinstance(writable_metric, WritableMetric), f"Expected writable_metric to be of type WritableMetric, got {type(writable_metric)}"
    assert writable_metric is not None, "WritableMetric should exist in the device"
    assert writable_metric.value == 100, f"Expected writable_metric value to be 100, got {writable_metric.value}"
    # Ensure cleanup happens even if the test fails


@pytest.mark.asyncio
async def test_today_message():
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = await create_mocked_hub()

    # Inject messages after the event is set
    inject_message(hub, "N/123/solarcharger/290/History/Daily/0/MaxPower", "{\"value\": 1}")
    inject_message(hub, "N/123/solarcharger/290/History/Daily/1/MaxPower", "{\"value\": 2}")
    await finalize_injection(hub)

    # Validate that the device has the metric we published
    device = hub.devices["solarcharger_290"]
    assert len(device._metrics) == 2, f"Expected 2 metrics, got {len(device._metrics)}"

    metric = device.get_metric_from_unique_id("123_solarcharger_290_solarcharger_max_power_today")
    assert metric is not None, "Metric should exist in the device"
    assert metric.value == 1, f"Expected metric value to be 1, got {metric.value}"

    metric = device.get_metric_from_unique_id("123_solarcharger_290_solarcharger_max_power_yesterday")
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
    assert new_desc.name == "Switch {output:switch_{output}_custom_name} State"
    assert new_desc.key_values["output"] == "1"

@pytest.mark.asyncio
async def test_expend_message():
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = await create_mocked_hub()

    # Inject messages after the event is set
    inject_message(hub, "N/123/switch/170/SwitchableOutput/output_2/State", "{\"value\": 1}")
    await finalize_injection(hub)

    # Validate that the device has the metric we published
    device = hub.devices["switch_170"]
    metric = device.get_metric_from_unique_id("123_switch_170_switch_2_state")
    assert metric is not None, "Metric should exist in the device"
    assert metric.generic_short_id == "switch_{output}_state"
    assert metric.key_values["output"] == "2"
    assert metric.value == GenericOnOff.On, f"Expected metric value to be GenericOnOff.On, got {metric.value}"

@pytest.mark.asyncio
async def test_expend_message_2():
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = await create_mocked_hub()

    # Inject messages after the event is set
    inject_message(hub, "N/123/battery/170/Voltages/Cell3", "{\"value\": 3.331}")
    await finalize_injection(hub)

    # Validate that the device has the metric we published
    device = hub.devices["battery_170"]
    metric = device.get_metric_from_unique_id("123_battery_170_battery_cell_3_voltage")
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
    inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 42}")
    await finalize_injection(hub, False)

    # Validate that the device has the metric we published
    device = hub.devices["grid_30"]
    metric = device.get_metric_from_unique_id("123_grid_30_grid_energy_forward_L1")
    assert metric is not None, "Metric should exist in the device"
    assert metric.value == 42, f"Expected metric value to be 42, got {metric.value}"
    metric.on_update = MagicMock()

    # Inject the same message again
    inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 42}")
    await asyncio.sleep(0.01)  # Allow event loop to process any scheduled callbacks
    assert metric.on_update.call_count == 0, "on_update should not be called for the same value"
    inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 43}")
    await asyncio.sleep(0.01)  # Allow event loop to process any scheduled callbacks
    assert metric.on_update.call_count == 1, "on_update should be called for the new value"

    await hub.disconnect()

@pytest.mark.asyncio
async def test_same_message_events_zero():
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = await create_mocked_hub(update_frequency_seconds=0)

    # Inject messages after the event is set
    inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 42}")
    await finalize_injection(hub, False)

    # Validate that the device has the metric we published
    device = hub.devices["grid_30"]
    metric = device.get_metric_from_unique_id("123_grid_30_grid_energy_forward_L1")
    assert metric is not None, "Metric should exist in the device"
    assert metric.value == 42, f"Expected metric value to be 42, got {metric.value}"
    metric.on_update = MagicMock()

    # Inject the same message again
    inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 42}")
    await asyncio.sleep(0.01)  # Allow event loop to process any scheduled callbacks
    assert metric.on_update.call_count == 1, "on_update should be called for the same value"
    inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 43}")
    await asyncio.sleep(0.01)  # Allow event loop to process any scheduled callbacks
    assert metric.on_update.call_count == 2, "on_update should be called for the new value"

    await hub.disconnect()

@pytest.mark.asyncio
@patch('victron_mqtt.metric.time.time')
async def test_same_message_events_five(mock_time):
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = await create_mocked_hub(update_frequency_seconds=5)

    mock_time.return_value = 10

    # Inject messages after the event is set
    inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 42}")
    await finalize_injection(hub, False)

    # Validate that the device has the metric we published
    device = hub.devices["grid_30"]
    metric = device.get_metric_from_unique_id("123_grid_30_grid_energy_forward_L1")
    assert metric is not None, "Metric should exist in the device"
    assert metric.value == 42, f"Expected metric value to be 42, got {metric.value}"
    metric.on_update = MagicMock()

    # Inject the same message again
    inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 42}")
    await asyncio.sleep(0.01)  # Allow event loop to process any scheduled callbacks
    assert metric.on_update.call_count == 1, "on_update should be called for the same value as this is the first notification"

    # Inject the same message again
    inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 42}")
    await asyncio.sleep(0.01)  # Allow event loop to process any scheduled callbacks
    assert metric.on_update.call_count == 1, "on_update should not be called for the same value as the clock did not move"

    mock_time.return_value = 20

    inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 42}")
    await asyncio.sleep(0.01)  # Allow event loop to process any scheduled callbacks
    assert metric.on_update.call_count == 2, "on_update should be called after frequency elapsed"

    inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 43}")
    await asyncio.sleep(0.01)  # Allow event loop to process any scheduled callbacks
    assert metric.on_update.call_count == 2, "on_update should not be called for the new value"

    await hub.disconnect()

@pytest.mark.asyncio
@patch('victron_mqtt.metric.time.time')
async def test_metric_keepalive_no_updates(mock_time):
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = await create_mocked_hub()

    mock_time.return_value = 10

    # Inject messages after the event is set
    inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 42}")
    await finalize_injection(hub, False)

    # Validate that the device has the metric we published
    device = hub.devices["grid_30"]
    metric = device.get_metric_from_unique_id("123_grid_30_grid_energy_forward_L1")
    assert metric is not None, "Metric should exist in the device"
    assert metric.value == 42, f"Expected metric value to be 42, got {metric.value}"
    magic_mock = MagicMock()
    metric.on_update = magic_mock

    # Calling keepalive fast so not expecting any updates
    mock_time.return_value = 20
    hub._keepalive_metrics()
    await asyncio.sleep(0.01)  # Allow event loop to process any scheduled callbacks
    assert metric.on_update.call_count == 0, "on_update should not be called as no invalidation occurred"

    # Invalidate all metrics
    mock_time.return_value = 90
    hub._keepalive_metrics()
    await asyncio.sleep(0.01)  # Allow event loop to process any scheduled callbacks
    assert metric.on_update.call_count == 1, "on_update should be called as metric updated to None"
    magic_mock.assert_called_with(metric, None)

    inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 42}")
    await asyncio.sleep(0.01)  # Allow event loop to process any scheduled callbacks
    assert metric.on_update.call_count == 2, "on_update should be called as metric updates back to value"
    magic_mock.assert_called_with(metric, 42)

    await hub.disconnect()

@pytest.mark.asyncio
@patch('victron_mqtt.metric.time.time')
async def test_metric_keepalive_with_updates(mock_time):
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = await create_mocked_hub(update_frequency_seconds=30)

    mock_time.return_value = 10

    # Inject messages after the event is set
    inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 42}")
    await finalize_injection(hub, False)

    # Validate that the device has the metric we published
    device = hub.devices["grid_30"]
    metric = device.get_metric_from_unique_id("123_grid_30_grid_energy_forward_L1")
    assert metric is not None, "Metric should exist in the device"
    assert metric.value == 42, f"Expected metric value to be 42, got {metric.value}"
    magic_mock = MagicMock()
    metric.on_update = magic_mock

    inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 43}")
    # Calling keepalive fast so not expecting any updates
    mock_time.return_value = 20
    hub._keepalive_metrics()
    await asyncio.sleep(0.01)  # Allow event loop to process any scheduled callbacks
    assert metric.on_update.call_count == 0, "on_update should not be called as no invalidation occurred"

    # Invalidate all metrics
    mock_time.return_value = 40
    hub._keepalive_metrics()
    await asyncio.sleep(0.01)  # Allow event loop to process any scheduled callbacks
    assert metric.on_update.call_count == 1, "on_update should be called as metric updated to None"
    magic_mock.assert_called_with(metric, 43)

    await hub.disconnect()

@pytest.mark.asyncio
async def test_existing_installation_id():
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = await create_mocked_hub(installation_id="123")

    # Inject messages after the event is set
    inject_message(hub, "N/123/switch/170/SwitchableOutput/output_2/State", "{\"value\": 1}")
    await finalize_injection(hub)

    # Validate that the device has the metric we published
    device = hub.devices["switch_170"]
    metric = device.get_metric_from_unique_id("123_switch_170_switch_2_state")
    assert metric is not None, "Metric should exist in the device"
    assert metric.generic_short_id == "switch_{output}_state"
    assert metric.key_values["output"] == "2"
    assert metric.value == GenericOnOff.On, f"Expected metric value to be GenericOnOff.On, got {metric.value}"


@pytest.mark.asyncio
async def test_multiple_hubs():
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub1: Hub = await create_mocked_hub()

    # Inject messages after the event is set
    inject_message(hub1, "N/123/switch/170/SwitchableOutput/output_2/State", "{\"value\": 1}")
    await finalize_injection(hub1, disconnect=False)

    # Validate that the device has the metric we published
    device1 = hub1.devices["switch_170"]
    metric1 = device1.get_metric_from_unique_id("123_switch_170_switch_2_state")
    assert metric1 is not None, "Metric should exist in the device"
    assert metric1.generic_short_id == "switch_{output}_state"
    assert metric1.key_values["output"] == "2"
    assert metric1.value == GenericOnOff.On, f"Expected metric value to be GenericOnOff.On, got {metric1.value}"

    hub2: Hub = await create_mocked_hub(installation_id="123")
    # Inject messages after the event is set
    inject_message(hub2, "N/123/switch/170/SwitchableOutput/output_2/State", "{\"value\": 0}")
    await finalize_injection(hub2, disconnect=False)

    # Validate the Hub's state
    assert len(hub2.devices) == 1, f"Expected 1 device, got {len(hub1.devices)}"

    # Validate that the device has the metric we published
    device2 = hub2.devices["switch_170"]
    metric2 = device2.get_metric_from_unique_id("123_switch_170_switch_2_state")
    assert metric2 is not None, "Metric should exist in the device"
    assert metric2.generic_short_id == "switch_{output}_state"
    assert metric2.key_values["output"] == "2"
    assert metric2.value == GenericOnOff.Off, f"Expected metric value to be GenericOnOff.Off, got {metric2.value}"

    await hub2.disconnect()
    await hub1.disconnect()

@pytest.mark.asyncio
async def test_float_precision():
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = await create_mocked_hub()

    # Inject messages after the event is set
    inject_message(hub, "N/123/system/170/Dc/System/Power", "{\"value\": 1.1234}")
    await finalize_injection(hub)

    # Validate that the device has the metric we published
    device = hub.devices["system_170"]
    metric = device.get_metric_from_unique_id("123_system_170_system_dc_consumption")
    assert metric is not None, "Metric should exist in the device"
    assert metric.value == 1.1, f"Expected metric value to be 1.1, got {metric.value}"

@pytest.mark.asyncio
async def test_float_precision_none():
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = await create_mocked_hub()

    # Inject messages after the event is set
    inject_message(hub, "N/123/gps/170/Position/Latitude", "{\"value\": 1.0123456789}")
    await finalize_injection(hub)

    # Validate that the device has the metric we published
    device = hub.devices["gps_170"]
    metric = device.get_metric_from_unique_id("123_gps_170_gps_latitude")
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
    inject_message(hub, "N/123/system/170/Dc/System/Power", "{\"value\": 1.1234}")
    inject_message(hub, "N/123/system/170/Dc/Battery/Power", "{\"value\": 120}") # Will generate also formula metrics.
    inject_message(hub, "N/123/gps/170/Position/Latitude", "{\"value\": 2.3456}")
    await finalize_injection(hub, disconnect=False)

    # Wait for the callback to be triggered
    await asyncio.sleep(0.1)  # Allow event loop to process the callback

    # Validate that the on_new_metric callback was called
    mock_on_new_metric.assert_any_call(hub, hub.devices["system_170"], hub.devices["system_170"].get_metric_from_unique_id("123_system_170_system_dc_consumption"))
    mock_on_new_metric.assert_any_call(hub, hub.devices["system_170"], hub.devices["system_170"].get_metric_from_unique_id("123_system_170_system_dc_battery_power"))
    mock_on_new_metric.assert_any_call(hub, hub.devices["gps_170"], hub.devices["gps_170"].get_metric_from_unique_id("123_gps_170_gps_latitude"))
    mock_on_new_metric.assert_any_call(hub, hub.devices["system_170"], hub.devices["system_170"].get_metric_from_unique_id("123_system_170_system_dc_battery_charge_energy"))
    mock_on_new_metric.assert_any_call(hub, hub.devices["system_170"], hub.devices["system_170"].get_metric_from_unique_id("123_system_170_system_dc_battery_discharge_energy"))
    assert mock_on_new_metric.call_count == 5, "on_new_metric should be called exactly 5 times"

    # Check that we got the callback only once
    await hub._keepalive()
    # Wait for the callback to be triggered
    await asyncio.sleep(0.1)  # Allow event loop to process the callback
    assert mock_on_new_metric.call_count == 5, "on_new_metric should be called exactly 5 times"

    # Validate that the device has the metric we published
    device = hub.devices["system_170"]
    metric = device.get_metric_from_unique_id("123_system_170_system_dc_consumption")
    assert metric is not None, "Metric should exist in the device"
    assert metric.value == 1.1, f"Expected metric value to be 1.1, got {metric.value}"
    await hub.disconnect()

@pytest.mark.asyncio
async def test_experimental_metrics_not_created_by_default():
    """Ensure experimental topics do not create devices/metrics when operation_mode is not EXPERIMENTAL."""
    hub: Hub = await create_mocked_hub()

    # Inject an experimental topic (generator TodayRuntime is marked experimental in _victron_topics)
    inject_message(hub, "N/123/generator/170/TodayRuntime", '{"value": 100}')
    await finalize_injection(hub)

    # The experimental topic should not have created a device or metric
    assert "generator_170" not in hub.devices, "Experimental topic should not create devices/metrics when operation_mode is not EXPERIMENTAL"

@pytest.mark.asyncio
async def test_experimental_metrics_created_when_needed():
    """Ensure experimental topics create devices/metrics when operation_mode is EXPERIMENTAL."""
    hub: Hub = await create_mocked_hub(operation_mode=OperationMode.EXPERIMENTAL)

    # Inject an experimental topic (generator TodayRuntime is marked experimental in _victron_topics)
    inject_message(hub, "N/123/generator/170/TodayRuntime", '{"value": 100}')
    await finalize_injection(hub)

    # The experimental topic should not have created a device or metric
    assert "generator_170" in hub.devices, "Experimental topic should not create devices/metrics when operation_mode is not EXPERIMENTAL"

@pytest.mark.asyncio
async def test_read_only_creates_plain_metrics():
    """Ensure that in READ_ONLY mode entities that are normally Switch/Number/Select are created as plain Metric."""
    hub: Hub = await create_mocked_hub(operation_mode=OperationMode.READ_ONLY)
    # Inject a topic that normally creates a Switch/Number (evcharger SetCurrent)
    inject_message(hub, "N/123/evcharger/170/SetCurrent", "{\"value\": 100}")
    await finalize_injection(hub)

    # Validate the Hub's state
    assert "evcharger_170" in hub.devices, "Device should be created"
    device = hub.devices["evcharger_170"]
    metric = device.get_metric_from_unique_id("123_evcharger_170_evcharger_set_current")
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
    inject_message(hub, "N/123/evcharger/170/SetCurrent", "{\"value\": 100}")

    # Validate the Hub's state
    assert len(hub.devices) == 1, f"Expected 1 device, got {len(hub.devices)}"
    assert "system_0" in hub.devices, "Expected only the system device to exist"

@pytest.mark.asyncio
async def test_filtered_message_system():
    """Test that the Hub correctly filters MQTT messages for system device type."""
    hub: Hub = await create_mocked_hub(device_type_exclude_filter=[DeviceType.SYSTEM], operation_mode=OperationMode.EXPERIMENTAL)

    # Inject messages after the event is set
    inject_message(hub, "N/123/system/0/Relay/0/State", "{\"value\": 1}")
    await finalize_injection(hub)

    # Validate the Hub's state - system device exists but has no metrics due to filtering
    assert len(hub.devices) == 1, f"Expected 1 device (system device), got {len(hub.devices)}"
    system_device = hub.devices["system_0"]
    assert len(system_device._metrics) == 0, f"Expected 0 metrics on system device due to filtering, got {len(system_device._metrics)}"

@pytest.mark.asyncio
async def test_no_filtered_message_placeholder():
    """Test that the Hub correctly filters MQTT messages for generator2 device type."""
    hub: Hub = await create_mocked_hub(device_type_exclude_filter=[DeviceType.GENERATOR0], operation_mode=OperationMode.EXPERIMENTAL)

    # Inject messages after the event is set
    inject_message(hub, "N/123/settings/0/Settings/Generator1/Soc/Enabled", "{\"value\": 1}")
    await finalize_injection(hub)

    # Validate the Hub's state - only system device exists, generator message was filtered
    assert len(hub.devices) == 2, f"Expected 2 devices (system and generator1), got {len(hub.devices)}"
    system_device = hub.devices["system_0"]
    assert system_device.device_type.value[0] == "system", f"Expected system device, got {system_device.device_type.value}"


@pytest.mark.asyncio
async def test_filtered_message_placeholder():
    """Test that the Hub correctly filters MQTT messages for generator1 device type."""
    hub: Hub = await create_mocked_hub(device_type_exclude_filter=[DeviceType.GENERATOR1], operation_mode=OperationMode.EXPERIMENTAL)

    # Inject messages after the event is set
    inject_message(hub, "N/123/settings/0/Settings/Generator1/Soc/Enabled", "{\"value\": 1}")
    await finalize_injection(hub)

    # Validate the Hub's state - only system device exists, generator message was filtered
    assert len(hub.devices) == 1, f"Expected 1 device (system device), got {len(hub.devices)}"
    system_device = hub.devices["system_0"]
    assert system_device.device_type.value[0] == "system", f"Expected system device, got {system_device.device_type.value}"


@pytest.mark.asyncio
async def test_remote_name_dont_exists():
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = await create_mocked_hub()

    inject_message(hub, "N/123/switch/170/SwitchableOutput/output_1/State", "{\"value\": 1}")
    await finalize_injection(hub)

    # Validate the Hub's state
    assert len(hub.devices) == 2, f"Expected 2 device, got {len(hub.devices)}"

    # Validate that the device has the metric we published
    device = hub.devices["switch_170"]
    assert len(device._metrics) == 1, f"Expected 1 metrics, got {len(device._metrics)}"
    metric = device.get_metric_from_unique_id("123_switch_170_switch_1_state")
    assert metric is not None, "metric should exist in the device"
    assert metric.name == "Switch 1 State", "Expected metric name to be 'Switch 1 State', got {metric.name}"
    assert metric.generic_name == "Switch {output} State", "Expected metric generic_name to be 'Switch {output} State', got {metric.generic_name}"
    assert metric.value == GenericOnOff.On, f"Expected metric value to be 1, got {metric.value}"
    assert metric.key_values["output"] == "1"

@pytest.mark.asyncio
async def test_remote_name_exists():
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = await create_mocked_hub()

    inject_message(hub, "N/123/switch/170/SwitchableOutput/output_1/State", "{\"value\": 1}")
    inject_message(hub, "N/123/switch/170/SwitchableOutput/output_1/Settings/CustomName", "{\"value\": \"bla\"}")
    await finalize_injection(hub)

    # Validate the Hub's state
    assert len(hub.devices) == 2, f"Expected 2 device, got {len(hub.devices)}"

    # Validate that the device has the metric we published
    device = hub.devices["switch_170"]
    assert len(device._metrics) == 2, f"Expected 2 metrics, got {len(device._metrics)}"
    metric = device.get_metric_from_unique_id("123_switch_170_switch_1_state")
    assert metric is not None, "metric should exist in the device"
    assert metric.name == "Switch bla State", "Expected metric name to be 'Switch bla State', got {metric.name}"
    assert metric.generic_name == "Switch {output} State", "Expected metric name to be 'Switch {output} State', got {metric.name}"
    assert metric.value == GenericOnOff.On, f"Expected metric value to be 1, got {metric.value}"
    assert metric.key_values["output"] == "bla"

@pytest.mark.asyncio
async def test_remote_name_exists_twodevices():
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = await create_mocked_hub()

    inject_message(hub, "N/123/switch/170/SwitchableOutput/output_1/State", "{\"value\": 1}")
    inject_message(hub, "N/123/switch/170/SwitchableOutput/output_1/Settings/CustomName", "{\"value\": \"bla\"}")
    inject_message(hub, "N/123/switch/155/SwitchableOutput/output_1/State", "{\"value\": 1}")
    inject_message(hub, "N/123/switch/155/SwitchableOutput/output_1/Settings/CustomName", "{\"value\": \"foo\"}")
    await finalize_injection(hub)

    # Validate the Hub's state
    assert len(hub.devices) == 3, f"Expected 3 device, got {len(hub.devices)}"

    # Validate that the device has the metric we published
    device = hub.devices["switch_170"]
    assert len(device._metrics) == 2, f"Expected 2 metrics, got {len(device._metrics)}"
    metric = device.get_metric_from_unique_id("123_switch_170_switch_1_state")
    assert metric is not None, "metric should exist in the device"
    assert metric.name == "Switch bla State", "Expected metric name to be 'Switch bla State', got {metric.name}"
    assert metric.generic_name == "Switch {output} State", "Expected metric name to be 'Switch {output} State', got {metric.name}"
    assert metric.value == GenericOnOff.On, f"Expected metric value to be 1, got {metric.value}"
    assert metric.key_values["output"] == "bla"

    device = hub.devices["switch_155"]
    assert len(device._metrics) == 2, f"Expected 2 metrics, got {len(device._metrics)}"
    metric = device.get_metric_from_unique_id("123_switch_155_switch_1_state")
    assert metric is not None, "metric should exist in the device"
    assert metric.name == "Switch foo State", "Expected metric name to be 'Switch foo State', got {metric.name}"
    assert metric.generic_name == "Switch {output} State", "Expected metric name to be 'Switch {output} State', got {metric.name}"
    assert metric.value == GenericOnOff.On, f"Expected metric value to be 1, got {metric.value}"
    assert metric.key_values["output"] == "foo"

@pytest.mark.asyncio
async def test_remote_name_exists_2():
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = await create_mocked_hub()

    inject_message(hub, "N/123/solarcharger/170/Pv/2/Name", "{\"value\": \"bar\"}")
    inject_message(hub, "N/123/solarcharger/170/Pv/2/P", "{\"value\": 1}")
    await finalize_injection(hub)

    # Validate the Hub's state
    assert len(hub.devices) == 2, f"Expected 2 device, got {len(hub.devices)}"

    # Validate that the device has the metric we published
    device = hub.devices["solarcharger_170"]
    assert len(device._metrics) == 2, f"Expected 2 metrics, got {len(device._metrics)}"
    metric = device.get_metric_from_unique_id("123_solarcharger_170_solarcharger_tracker_2_power")
    assert metric is not None, "metric should exist in the device"
    assert metric.name == "PV Tracker bar Power", "Expected metric name to be 'PV Tracker bar Power', got {metric.name}"
    assert metric.generic_name == "PV Tracker {tracker} Power", "Expected metric name to be 'PV Tracker {tracker} Power', got {metric.name}"
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
    hub._on_connect_internal(mocked_client, None, {}, 0, None)

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
    """Test that the Hub correctly filters MQTT messages for generator1 device type."""
    hub: Hub = await create_mocked_hub()

    # Inject messages after the event is set
    inject_message(hub, "N/123/evcharger/170/SetCurrent", "{\"value\": null}")
    await finalize_injection(hub)

    # Validate the Hub's state - only system device exists, evcharger message was filtered
    assert len(hub.devices) == 2, f"Expected 2 device (system device), got {len(hub.devices)}"
    device = hub.devices["evcharger_170"]
    assert device.metrics == [], f"Expected 0 metrics on evcharger device due to null message, got {len(device._metrics)}"

@pytest.mark.asyncio
@patch('victron_mqtt.formula_common.datetime')
async def test_formula_message(mock_datetime):
    """Test that the Hub correctly filters MQTT messages for generator1 device type."""
    # Mock datetime.now() to return a fixed time
    fixed_time = datetime(year=2025, month=1, day=1, hour=12, minute=0, second=0)
    mock_datetime.now.return_value = fixed_time

    hub: Hub = await create_mocked_hub(operation_mode=OperationMode.EXPERIMENTAL)

    # Inject messages after the event is set
    inject_message(hub, "N/123/system/0/Dc/Battery/Power", "{\"value\": 120}")
    await finalize_injection(hub, disconnect=False)

    # Validate the Hub's state - only system device exists, evcharger message was filtered
    assert len(hub.devices) == 1, f"Expected 1 device (system device), got {len(hub.devices)}"
    device = hub.devices["system_0"]
    assert len(device._metrics) == 3, f"Expected 3 metrics, got {len(device._metrics)}"
    metric1 = device.get_metric_from_unique_id("123_system_0_system_dc_battery_power")
    assert metric1 is not None, "metric should exist in the device"
    assert metric1.value == 120, f"Expected metric value to be 120, got {metric1.value}"

    metric2 = device.get_metric_from_unique_id("123_system_0_system_dc_battery_charge_energy")
    assert metric2 is not None, "metric should exist in the device"
    assert metric2.value == 0.0, f"Expected metric value to be 0.0, got {metric2.value}"
    assert metric2.generic_short_id == "system_dc_battery_charge_energy", f"Expected generic_short_id to be 'system_dc_battery_charge_energy', got {metric2.generic_short_id}"
    assert metric2.name == "DC Battery Charge Energy", f"Expected name to be 'DC Battery Charge Energy', got {metric2.name}"

    metric3 = device.get_metric_from_unique_id("123_system_0_system_dc_battery_discharge_energy")
    assert metric3 is not None, "metric should exist in the device"
    assert metric3.value == 0.0, f"Expected metric value to be 0.0, got {metric3.value}"
    assert metric3.generic_short_id == "system_dc_battery_discharge_energy", f"Expected generic_short_id to be 'system_dc_battery_discharge_energy', got {metric3.generic_short_id}"
    assert metric3.name == "DC Battery Discharge Energy", f"Expected name to be 'DC Battery Discharge Energy', got {metric3.name}"

    fixed_time = datetime(year=2025, month=1, day=1, hour=12, minute=0, second=15)
    mock_datetime.now.return_value = fixed_time
    inject_message(hub, "N/123/system/0/Dc/Battery/Power", "{\"value\": 80}")
    assert metric2.value == 0.5, f"Expected metric value to be 0.5, got {metric2.value}"

    fixed_time = datetime(year=2025, month=1, day=1, hour=12, minute=0, second=30)
    mock_datetime.now.return_value = fixed_time
    inject_message(hub, "N/123/system/0/Dc/Battery/Power", "{\"value\": -100}")
    assert metric2.value == 0.8, f"Expected metric value to be 0.8, got {metric2.value}"

    fixed_time = datetime(year=2025, month=1, day=1, hour=12, minute=0, second=45)
    mock_datetime.now.return_value = fixed_time
    inject_message(hub, "N/123/system/0/Dc/Battery/Power", "{\"value\": -200}")
    assert metric2.value == 0.8, f"Expected metric value to be 0.8, got {metric2.value}"
    assert metric3.value == 0.4, f"Expected metric value to be 0.4, got {metric3.value}"

    await hub.disconnect()
