import pytest
import pytest_asyncio
import asyncio
from unittest.mock import MagicMock, patch
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

@pytest_asyncio.fixture
async def create_mocked_hub_with_installation_id() -> Hub:
    return await create_mocked_hub_internal(installation_id="123")

@pytest_asyncio.fixture
async def create_mocked_hub() -> Hub:
    return await create_mocked_hub_internal()

@pytest_asyncio.fixture
async def create_mocked_hub_read_only() -> Hub:
    """Fixture returning a hub set to READ_ONLY operation mode."""
    return await create_mocked_hub_internal(operation_mode=OperationMode.READ_ONLY)

@pytest_asyncio.fixture
async def create_mocked_hub_experimental() -> Hub:
    """Fixture returning a hub set to EXPERIMENTAL operation mode."""
    return await create_mocked_hub_internal(operation_mode=OperationMode.EXPERIMENTAL)

async def create_mocked_hub_internal(installation_id=None, operation_mode: OperationMode = OperationMode.FULL, device_type_exclude_filter: list[DeviceType] | None = None) -> Hub:
    """Helper function to create and return a mocked Hub object."""
    with patch('victron_mqtt.hub.mqtt.Client') as mock_client:
        hub = Hub(host="localhost", port=1883, username=None, password=None, use_ssl=False, installation_id = installation_id, operation_mode=operation_mode, device_type_exclude_filter=device_type_exclude_filter)
        mocked_client = mock_client.return_value

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
async def test_hub_initialization(create_mocked_hub):
    """Test that the Hub initializes correctly."""
    hub: Hub = create_mocked_hub
    assert hub._client is not None, "MQTT client should be initialized"

@pytest.mark.asyncio
async def test_hub_message_handling(create_mocked_hub):
    """Test that the Hub processes incoming MQTT messages correctly."""
    hub: Hub = create_mocked_hub

    # Inject a message
    inject_message(hub, "N/device/123/metric/456", "{\"value\": 42}")

    # Validate the Hub's state
    assert len(hub._devices) == 1, "No devices should be created"

    await finalize_injection(hub)

@pytest.mark.asyncio
async def test_phase_message(create_mocked_hub):
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = create_mocked_hub

    # Inject messages after the event is set
    inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 42}")
    await finalize_injection(hub)

    # Validate the Hub's state
    assert len(hub._devices) == 2, f"Expected 2 device, got {len(hub._devices)}"

    # Validate that the device has the metric we published
    device = hub._devices["123_grid_30"]
    assert device.device_type == DeviceType.GRID, f"Expected metric type to be 'grid', got {device.device_type}"
    metric = device.get_metric_from_unique_id("123_grid_30_grid_energy_forward_L1")
    assert metric is not None, "Metric should exist in the device"
    assert metric.value == 42, f"Expected metric value to be 42, got {metric.value}"
    assert metric.short_id == "grid_energy_forward_L1", f"Expected metric short_id to be 'grid_energy_forward_L1', got {metric.short_id}"
    assert metric.generic_short_id == "grid_energy_forward_{phase}", f"Expected metric generic_short_id to be 'grid_energy_forward_{{phase}}', got {metric.generic_short_id}"
    assert metric.unique_id == "123_grid_30_grid_energy_forward_L1", f"Expected metric unique_id to be '123_grid_30_grid_energy_forward_L1', got {metric.unique_id}"
    assert metric.name == "Grid consumption on L1", f"Expected metric name to be 'Grid consumption on L1', got {metric.name}"
    assert metric.unit_of_measurement == "kWh", f"Expected metric unit_of_measurement to be 'kWh', got {metric.unit_of_measurement}"

@pytest.mark.asyncio
async def test_placeholder_message(create_mocked_hub):
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = create_mocked_hub

    # Inject messages after the event is set
    inject_message(hub, "N/123/system/0/Relay/0/State", "{\"value\": 1}")
    await finalize_injection(hub)

    # Validate the Hub's state
    assert len(hub._devices) == 1, f"Expected 1 device, got {len(hub._devices)}"

    # Validate that the device has the metric we published
    device =hub._devices["123_system_0"]
    metric = device.get_metric_from_unique_id("123_system_0_system_relay_0")
    assert metric is not None, "Metric should exist in the device"
    assert metric.value == GenericOnOff.On, f"Expected metric value to be GenericOnOff.On, got {metric.value}"

@pytest.mark.asyncio
async def test_dynamic_min_max_message(create_mocked_hub):
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = create_mocked_hub

    # Inject messages after the event is set
    inject_message(hub, "N/123/settings/0/Settings/CGwacs/AcPowerSetPoint", '{"max": 1000000, "min": -1000000, "value": 50}')
    await finalize_injection(hub)

    # Validate the Hub's state
    assert len(hub._devices) == 1, f"Expected 1 device, got {len(hub._devices)}"

    # Validate that the device has the metric we published
    device = list(hub._devices.values())[0]
    writable_metric = device.get_metric_from_unique_id("123_system_0_system_ac_power_set_point")
    assert writable_metric is not None, "WritableMetric should exist in the device"
    assert isinstance(writable_metric, WritableMetric), f"Expected writable_metric to be of type WritableMetric, got {type(writable_metric)}"
    assert writable_metric.value == 50, f"Expected writable_metric value to be 50, got {writable_metric.value}"
    assert writable_metric.min_value == -1000000, f"Expected writable_metric min to be -1000000, got {writable_metric.min_value}"
    assert writable_metric.max_value == 1000000, f"Expected writable_metric max to be 1000000, got {writable_metric.max_value}"

@pytest.mark.asyncio
async def test_number_message(create_mocked_hub):
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = create_mocked_hub

    # Inject messages after the event is set
    inject_message(hub, "N/123/evcharger/170/SetCurrent", "{\"value\": 100}")

    # Validate the Hub's state
    assert len(hub._devices) == 2, f"Expected 2 device, got {len(hub._devices)}"

    # Validate that the device has the metric we published
    device = hub._devices["123_evcharger_170"]
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

    await finalize_injection(hub)


@pytest.mark.asyncio
async def test_placeholder_adjustable_on(create_mocked_hub):
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = create_mocked_hub

    # Inject messages after the event is set
    inject_message(hub, "N/123/vebus/170/Ac/ActiveIn/CurrentLimit", "{\"value\": 100}")
    inject_message(hub, "N/123/vebus/170/Ac/ActiveIn/CurrentLimitIsAdjustable", "{\"value\": 1}")
    await finalize_injection(hub)

    # Validate the Hub's state
    assert len(hub._devices) == 2, f"Expected 2 device, got {len(hub._devices)}"

    # Validate that the device has the metric we published
    device = hub._devices["123_vebus_170"]
    assert len(device._metrics) == 1, f"Expected 1 metrics, got {len(device._metrics)}"
    writable_metric = device.get_metric_from_unique_id("123_vebus_170_vebus_inverter_current_limit")
    assert isinstance(writable_metric, WritableMetric), f"Expected writable_metric to be of type WritableMetric, got {type(writable_metric)}"
    assert writable_metric is not None, "WritableMetric should exist in the device"
    assert writable_metric.value == 100, f"Expected writable_metric value to be 100, got {writable_metric.value}"
    # Ensure cleanup happens even if the test fails

@pytest.mark.asyncio
async def test_placeholder_adjustable_off(create_mocked_hub):
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = create_mocked_hub

    # Inject messages after the event is set
    inject_message(hub, "N/123/vebus/170/Ac/ActiveIn/CurrentLimit", "{\"value\": 100}")
    inject_message(hub, "N/123/vebus/170/Ac/ActiveIn/CurrentLimitIsAdjustable", "{\"value\": 0}")
    await finalize_injection(hub)

    # Validate the Hub's state
    assert len(hub._devices) == 2, f"Expected 2 device, got {len(hub._devices)}"

    # Validate that the device has the metric we published
    device = hub._devices["123_vebus_170"]
    assert len(device._metrics) == 1, f"Expected 1 metrics, got {len(device._metrics)}"
    writable_metric = device.get_metric_from_unique_id("123_vebus_170_vebus_inverter_current_limit")
    assert not isinstance(writable_metric, WritableMetric), f"Expected writable_metric to be of type Metric, got {type(writable_metric)}"
    assert writable_metric is not None, "WritableMetric should exist in the device"
    assert writable_metric.value == 100, f"Expected writable_metric value to be 100, got {writable_metric.value}"
    # Ensure cleanup happens even if the test fails

@pytest.mark.asyncio
async def test_placeholder_adjustable_on_reverse(create_mocked_hub):
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = create_mocked_hub

    # Inject messages after the event is set
    inject_message(hub, "N/123/vebus/170/Ac/ActiveIn/CurrentLimitIsAdjustable", "{\"value\": 1}")
    inject_message(hub, "N/123/vebus/170/Ac/ActiveIn/CurrentLimit", "{\"value\": 100}")
    await finalize_injection(hub)

    # Validate that the device has the metric we published
    device = hub._devices["123_vebus_170"]
    assert len(device._metrics) == 1, f"Expected 1 metrics, got {len(device._metrics)}"
    writable_metric = device.get_metric_from_unique_id("123_vebus_170_vebus_inverter_current_limit")
    assert isinstance(writable_metric, WritableMetric), f"Expected writable_metric to be of type WritableMetric, got {type(writable_metric)}"
    assert writable_metric is not None, "WritableMetric should exist in the device"
    assert writable_metric.value == 100, f"Expected writable_metric value to be 100, got {writable_metric.value}"
    # Ensure cleanup happens even if the test fails

@pytest.mark.asyncio
async def test_placeholder_adjustable_off_reverse(create_mocked_hub):
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = create_mocked_hub

    # Inject messages after the event is set
    inject_message(hub, "N/123/vebus/170/Ac/ActiveIn/CurrentLimitIsAdjustable", "{\"value\": 0}")
    inject_message(hub, "N/123/vebus/170/Ac/ActiveIn/CurrentLimit", "{\"value\": 100}")
    await finalize_injection(hub)

    # Validate that the device has the metric we published
    device = hub._devices["123_vebus_170"]
    assert len(device._metrics) == 1, f"Expected 1 metrics, got {len(device._metrics)}"
    writable_metric = device.get_metric_from_unique_id("123_vebus_170_vebus_inverter_current_limit")
    assert not isinstance(writable_metric, WritableMetric), f"Expected writable_metric to be of type WritableMetric, got {type(writable_metric)}"
    assert writable_metric is not None, "WritableMetric should exist in the device"
    assert writable_metric.value == 100, f"Expected writable_metric value to be 100, got {writable_metric.value}"
    # Ensure cleanup happens even if the test fails


@pytest.mark.asyncio
async def test_today_message(create_mocked_hub):
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = create_mocked_hub

    # Inject messages after the event is set
    inject_message(hub, "N/123/solarcharger/290/History/Daily/0/MaxPower", "{\"value\": 1}")
    inject_message(hub, "N/123/solarcharger/290/History/Daily/1/MaxPower", "{\"value\": 2}")
    await finalize_injection(hub)

    # Validate that the device has the metric we published
    device = hub._devices["123_solarcharger_290"]
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
    assert new_desc.name == "Switch {output} State"
    assert new_desc.key_values["output"] == "1"

@pytest.mark.asyncio
async def test_expend_message(create_mocked_hub):
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = create_mocked_hub

    # Inject messages after the event is set
    inject_message(hub, "N/123/switch/170/SwitchableOutput/output_2/State", "{\"value\": 1}")
    await finalize_injection(hub)

    # Validate that the device has the metric we published
    device = hub._devices["123_switch_170"]
    metric = device.get_metric_from_unique_id("123_switch_170_switch_2_state")
    assert metric is not None, "Metric should exist in the device"
    assert metric.generic_short_id == "switch_{output}_state"
    assert metric.key_values["output"] == "2"
    assert metric.value == GenericOnOff.On, f"Expected metric value to be GenericOnOff.On, got {metric.value}"

@pytest.mark.asyncio
async def test_expend_message_2(create_mocked_hub):
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = create_mocked_hub

    # Inject messages after the event is set
    inject_message(hub, "N/123/battery/170/Voltages/Cell3", "{\"value\": 3.331}")
    await finalize_injection(hub)

    # Validate that the device has the metric we published
    device = hub._devices["123_battery_170"]
    metric = device.get_metric_from_unique_id("123_battery_170_battery_cell_3_voltage")
    assert metric is not None, "Metric should exist in the device"
    assert metric.generic_short_id == "battery_cell_{cell_id}_voltage"
    assert metric.key_values["cell_id"] == "3"
    assert metric.value == 3.331, f"Expected metric value to be 3.331, got {metric.value}"

@pytest.mark.asyncio
async def test_same_message_events(create_mocked_hub):
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = create_mocked_hub

    # Inject messages after the event is set
    inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 42}")
    await finalize_injection(hub, False)

    # Validate that the device has the metric we published
    device = hub._devices["123_grid_30"]
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
async def test_existing_installation_id(create_mocked_hub_with_installation_id):
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = create_mocked_hub_with_installation_id

    # Inject messages after the event is set
    inject_message(hub, "N/123/switch/170/SwitchableOutput/output_2/State", "{\"value\": 1}")
    await finalize_injection(hub)

    # Validate that the device has the metric we published
    device = hub._devices["123_switch_170"]
    metric = device.get_metric_from_unique_id("123_switch_170_switch_2_state")
    assert metric is not None, "Metric should exist in the device"
    assert metric.generic_short_id == "switch_{output}_state"
    assert metric.key_values["output"] == "2"
    assert metric.value == GenericOnOff.On, f"Expected metric value to be GenericOnOff.On, got {metric.value}"


@pytest.mark.asyncio
async def test_multiple_hubs(create_mocked_hub_with_installation_id, create_mocked_hub):
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub1: Hub = create_mocked_hub

    # Inject messages after the event is set
    inject_message(hub1, "N/123/switch/170/SwitchableOutput/output_2/State", "{\"value\": 1}")
    await finalize_injection(hub1, disconnect=False)

    # Validate that the device has the metric we published
    device1 = hub1._devices["123_switch_170"]
    metric1 = device1.get_metric_from_unique_id("123_switch_170_switch_2_state")
    assert metric1 is not None, "Metric should exist in the device"
    assert metric1.generic_short_id == "switch_{output}_state"
    assert metric1.key_values["output"] == "2"
    assert metric1.value == GenericOnOff.On, f"Expected metric value to be GenericOnOff.On, got {metric1.value}"

    hub2: Hub = create_mocked_hub_with_installation_id
    # Inject messages after the event is set
    inject_message(hub2, "N/123/switch/170/SwitchableOutput/output_2/State", "{\"value\": 0}")
    await finalize_injection(hub1, disconnect=False)

    # Validate the Hub's state
    assert len(hub2._devices) == 1, f"Expected 1 device, got {len(hub1._devices)}"

    # Validate that the device has the metric we published
    device2 = hub2._devices["123_switch_170"]
    metric2 = device2.get_metric_from_unique_id("123_switch_170_switch_2_state")
    assert metric2 is not None, "Metric should exist in the device"
    assert metric2.generic_short_id == "switch_{output}_state"
    assert metric2.key_values["output"] == "2"
    assert metric2.value == GenericOnOff.Off, f"Expected metric value to be GenericOnOff.Off, got {metric2.value}"

    await hub2.disconnect()
    await hub1.disconnect()

@pytest.mark.asyncio
async def test_float_precision(create_mocked_hub):
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = create_mocked_hub

    # Inject messages after the event is set
    inject_message(hub, "N/123/system/170/Dc/System/Power", "{\"value\": 1.1234}")
    await finalize_injection(hub)

    # Validate that the device has the metric we published
    device = hub._devices["123_system_170"]
    metric = device.get_metric_from_unique_id("123_system_170_system_dc_consumption")
    assert metric is not None, "Metric should exist in the device"
    assert metric.value == 1.1, f"Expected metric value to be 1.1, got {metric.value}"

@pytest.mark.asyncio
async def test_float_precision_none(create_mocked_hub):
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub: Hub = create_mocked_hub

    # Inject messages after the event is set
    inject_message(hub, "N/123/gps/170/Position/Latitude", "{\"value\": 1.0123456789}")
    await finalize_injection(hub)

    # Validate that the device has the metric we published
    device = hub._devices["123_gps_170"]
    metric = device.get_metric_from_unique_id("123_gps_170_gps_latitude")
    assert metric is not None, "Metric should exist in the device"
    assert metric.value == 1.0123456789, f"Expected metric value to be 1.0123456789, got {metric.value}"

@pytest.mark.asyncio
async def test_new_metric(create_mocked_hub):
    """Test that the Hub correctly triggers the on_new_metric callback."""
    hub: Hub = create_mocked_hub

    # Mock the on_new_metric callback
    def on_new_metric_mock(hub, device, metric):
        logger.debug(f"New metric added: Hub={hub}, Device={device}, Metric={repr(metric)}")
    hub.on_new_metric = MagicMock(side_effect=on_new_metric_mock)

    # Inject messages after the event is set
    inject_message(hub, "N/123/system/170/Dc/System/Power", "{\"value\": 1.1234}")
    await finalize_injection(hub, disconnect=False)

    # Wait for the callback to be triggered
    await asyncio.sleep(0.1)  # Allow event loop to process the callback

    # Validate that the on_new_metric callback was called
    hub.on_new_metric.assert_called_once()

    # Check that we got the callback only once
    await hub._keepalive()
    # Wait for the callback to be triggered
    await asyncio.sleep(0.1)  # Allow event loop to process the callback
    hub.on_new_metric.assert_called_once()

    # Validate that the device has the metric we published
    device = hub._devices["123_system_170"]
    metric = device.get_metric_from_unique_id("123_system_170_system_dc_consumption")
    assert metric is not None, "Metric should exist in the device"
    assert metric.value == 1.1, f"Expected metric value to be 1.1, got {metric.value}"


    await hub.disconnect()

@pytest.mark.asyncio
async def test_experimental_metrics_not_created_by_default(create_mocked_hub):
    """Ensure experimental topics do not create devices/metrics when operation_mode is not EXPERIMENTAL."""
    hub: Hub = create_mocked_hub

    # Inject an experimental topic (generator TodayRuntime is marked experimental in _victron_topics)
    inject_message(hub, "N/123/generator/170/TodayRuntime", '{"value": 100}')
    await finalize_injection(hub)

    # The experimental topic should not have created a device or metric
    assert "123_generator_170" not in hub._devices, "Experimental topic should not create devices/metrics when operation_mode is not EXPERIMENTAL"

@pytest.mark.asyncio
async def test_experimental_metrics_created_when_needed(create_mocked_hub_experimental):
    """Ensure experimental topics create devices/metrics when operation_mode is EXPERIMENTAL."""
    hub: Hub = create_mocked_hub_experimental

    # Inject an experimental topic (generator TodayRuntime is marked experimental in _victron_topics)
    inject_message(hub, "N/123/generator/170/TodayRuntime", '{"value": 100}')
    await finalize_injection(hub)

    # The experimental topic should not have created a device or metric
    assert "123_generator_170" in hub._devices, "Experimental topic should not create devices/metrics when operation_mode is not EXPERIMENTAL"

@pytest.mark.asyncio
async def test_read_only_creates_plain_metrics(create_mocked_hub_read_only):
    """Ensure that in READ_ONLY mode entities that are normally Switch/Number/Select are created as plain Metric."""
    hub: Hub = create_mocked_hub_read_only
    # Inject a topic that normally creates a Switch/Number (evcharger SetCurrent)
    inject_message(hub, "N/123/evcharger/170/SetCurrent", "{\"value\": 100}")
    await finalize_injection(hub)

    # Validate the Hub's state
    assert "123_evcharger_170" in hub._devices, "Device should be created"
    device = hub._devices["123_evcharger_170"]
    metric = device.get_metric_from_unique_id("123_evcharger_170_evcharger_set_current")
    assert metric is not None, "Metric should exist in the device"
    assert not isinstance(metric, WritableMetric), "In READ_ONLY mode the metric should NOT be a WritableMetric"
    assert isinstance(metric, Metric), "In READ_ONLY mode the metric should be a plain Metric"

@pytest.mark.asyncio
async def test_publish(create_mocked_hub_experimental):
    hub: Hub = create_mocked_hub_experimental
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
async def test_publish_topic_not_found(create_mocked_hub_experimental):
    hub: Hub = create_mocked_hub_experimental
    mocked_client: MagicMock = hub._client # type: ignore

    # Clear any previous publish calls recorded by the mocked client
    if hasattr(mocked_client.publish, 'reset_mock'):
        mocked_client.publish.reset_mock()

    # Call the publish helper which should result in an internal client.publish call
    with pytest.raises(TopicNotFoundError):
        hub.publish("NO TOPIC", "170", 1)

    # Finalize injection to allow any keepalive/full-publish flows to complete
    await finalize_injection(hub)

# Device Type Filter Tests
@pytest.fixture
def create_mocked_hub_with_device_filter():
    """Fixture factory that returns a function to create mocked Hub with device filter."""
    async def _create_hub(device_type_exclude_filter: list[DeviceType]) -> Hub:
        """Helper function to create and return a mocked Hub object with specific device type filter."""
        return await create_mocked_hub_internal(device_type_exclude_filter=device_type_exclude_filter, operation_mode=OperationMode.EXPERIMENTAL)
    return _create_hub

@pytest.mark.asyncio
async def test_filtered_message(create_mocked_hub_with_device_filter):
    """Test that the Hub correctly filters MQTT messages for EVCHARGER device type."""
    hub: Hub = await create_mocked_hub_with_device_filter([DeviceType.EVCHARGER])

    # Inject messages after the event is set
    inject_message(hub, "N/123/evcharger/170/SetCurrent", "{\"value\": 100}")

    # Validate the Hub's state
    assert len(hub._devices) == 1, f"Expected 1 device, got {len(hub._devices)}"
    assert "123_system_0" in hub._devices, "Expected only the system device to exist"

@pytest.mark.asyncio
async def test_filtered_message_system(create_mocked_hub_with_device_filter):
    """Test that the Hub correctly filters MQTT messages for system device type."""
    hub: Hub = await create_mocked_hub_with_device_filter([DeviceType.SYSTEM])

    # Inject messages after the event is set
    inject_message(hub, "N/123/system/0/Relay/0/State", "{\"value\": 1}")
    await finalize_injection(hub)

    # Validate the Hub's state - system device exists but has no metrics due to filtering
    assert len(hub._devices) == 1, f"Expected 1 device (system device), got {len(hub._devices)}"
    system_device = hub._devices["123_system_0"]
    assert len(system_device._metrics) == 0, f"Expected 0 metrics on system device due to filtering, got {len(system_device._metrics)}"

@pytest.mark.asyncio
async def test_no_filtered_message_placeholder(create_mocked_hub_with_device_filter):
    """Test that the Hub correctly filters MQTT messages for generator2 device type."""
    hub: Hub = await create_mocked_hub_with_device_filter([DeviceType.GENERATOR0])

    # Inject messages after the event is set
    inject_message(hub, "N/123/settings/0/Settings/Generator1/Soc/Enabled", "{\"value\": 1}")
    await finalize_injection(hub)

    # Validate the Hub's state - only system device exists, generator message was filtered
    assert len(hub._devices) == 2, f"Expected 2 devices (system and generator1), got {len(hub._devices)}"
    system_device = hub._devices["123_system_0"]
    assert system_device.device_type.value[0] == "system", f"Expected system device, got {system_device.device_type.value}"


@pytest.mark.asyncio
async def test_filtered_message_placeholder(create_mocked_hub_with_device_filter):
    """Test that the Hub correctly filters MQTT messages for generator1 device type."""
    hub: Hub = await create_mocked_hub_with_device_filter([DeviceType.GENERATOR1])

    # Inject messages after the event is set
    inject_message(hub, "N/123/settings/0/Settings/Generator1/Soc/Enabled", "{\"value\": 1}")
    await finalize_injection(hub)

    # Validate the Hub's state - only system device exists, generator message was filtered
    assert len(hub._devices) == 1, f"Expected 1 device (system device), got {len(hub._devices)}"
    system_device = hub._devices["123_system_0"]
    assert system_device.device_type.value[0] == "system", f"Expected system device, got {system_device.device_type.value}"
