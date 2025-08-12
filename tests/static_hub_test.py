import pytest
import asyncio
from unittest.mock import MagicMock, patch
from victron_mqtt._victron_enums import DeviceType, GenericOnOff
from victron_mqtt.data_classes import TopicDescriptor
from victron_mqtt.hub import Hub
from victron_mqtt.constants import TOPIC_INSTALLATION_ID
from victron_mqtt.switch import Switch
from victron_mqtt._victron_topics import topics

@pytest.fixture
async def create_mocked_hub_with_installation_id():
    return await create_mocked_hub_internal(installation_id="123")

@pytest.fixture
async def create_mocked_hub():
    return await create_mocked_hub_internal()

async def create_mocked_hub_internal(installation_id=None):
    """Helper function to create and return a mocked Hub object."""
    with patch('victron_mqtt.hub.mqtt.Client') as mock_client:
        hub = Hub(host="localhost", port=1883, username=None, password=None, use_ssl=False, installation_id = installation_id)
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
        setattr(hub, '_subscribe', MagicMock(name="_subscribe", side_effect=mock_subscribe))

        # Mock publish to set an event when the keepalive topic is received
        keepalive_event = asyncio.Event()

        def mock_publish(topic, value):
            if topic == "R/123/keepalive":
                keepalive_event.set()
        setattr(hub, 'publish', MagicMock(name="publish", side_effect=mock_publish))

        # Dynamically add the keepalive_event attribute to the Hub instance
        setattr(hub, 'keepalive_event', keepalive_event)

        # Run connect as an asyncio task
        connect_task = asyncio.create_task(hub.connect())

        # Wait for the keepalive event before returning the hub
        await keepalive_event.wait()

        return hub, connect_task

def inject_message(hub_instance, topic, payload):
    """Helper function to inject a single MQTT message into the Hub."""
    hub_instance._client.on_message(None, None, MagicMock(topic=topic, payload=payload.encode()))

@pytest.mark.asyncio
async def test_hub_initialization(create_mocked_hub):
    """Test that the Hub initializes correctly."""
    hub, _ = await create_mocked_hub
    assert hub._client is not None, "MQTT client should be initialized"

@pytest.mark.asyncio
async def test_hub_message_handling(create_mocked_hub):
    """Test that the Hub processes incoming MQTT messages correctly."""
    hub, _ = await create_mocked_hub

    # Inject a message
    inject_message(hub, "N/device/123/metric/456", "{\"value\": 42}")

    # Validate the Hub's state
    assert len(hub._devices) == 0, "No devices should be created"

async def finalize_injection(hub, connect_task, disconnect: bool = True):
    """Finalize the injection of messages into the Hub."""
    inject_message(hub, "full_publish_completed", "1")
    # Wait for the connect task to finish
    await connect_task
    if disconnect:
        await hub.disconnect()

@pytest.mark.asyncio
async def test_phase_message(create_mocked_hub):
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub, connect_task = await create_mocked_hub

    # Inject messages after the event is set
    inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 42}")
    await finalize_injection(hub, connect_task)

    # Validate the Hub's state
    assert len(hub._devices) == 1, f"Expected 1 device, got {len(hub._devices)}"

    # Validate that the device has the metric we published
    device = list(hub._devices.values())[0]
    metric = device.get_metric_from_unique_id("123_grid_30_grid_energy_forward_L1")
    assert metric is not None, "Metric should exist in the device"
    assert metric.value == 42, f"Expected metric value to be 42, got {metric.value}"
    assert metric.device_type == DeviceType.GRID, f"Expected metric type to be 'grid', got {metric.device_type}"
    assert metric.short_id == "grid_energy_forward_L1", f"Expected metric short_id to be 'grid_energy_forward_L1', got {metric.short_id}"
    assert metric.generic_short_id == "grid_energy_forward_{phase}", f"Expected metric generic_short_id to be 'grid_energy_forward_{{phase}}', got {metric.generic_short_id}"
    assert metric.unique_id == "123_grid_30_grid_energy_forward_L1", f"Expected metric unique_id to be '123_grid_30_grid_energy_forward_L1', got {metric.unique_id}"
    assert metric.name == "Grid consumption on L1", f"Expected metric name to be 'Grid consumption on L1', got {metric.name}"
    assert metric.unit_of_measurement == "kWh", f"Expected metric unit_of_measurement to be 'kWh', got {metric.unit_of_measurement}"

@pytest.mark.asyncio
async def test_placeholder_message(create_mocked_hub):
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub, connect_task = await create_mocked_hub

    # Inject messages after the event is set
    inject_message(hub, "N/123/system/170/Relay/0/State", "{\"value\": 1}")
    await finalize_injection(hub, connect_task)

    # Validate the Hub's state
    assert len(hub._devices) == 1, f"Expected 1 device, got {len(hub._devices)}"

    # Validate that the device has the metric we published
    device = list(hub._devices.values())[0]
    metric = device.get_metric_from_unique_id("123_system_170_system_relay_0")
    assert metric is not None, "Metric should exist in the device"
    assert metric.value == GenericOnOff.On, f"Expected metric value to be GenericOnOff.On, got {metric.value}"

@pytest.mark.asyncio
async def test_dynamic_min_max_message(create_mocked_hub):
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub, connect_task = await create_mocked_hub

    # Inject messages after the event is set
    inject_message(hub, "N/123/settings/0/Settings/CGwacs/AcPowerSetPoint", '{"max": 1000000, "min": -1000000, "value": 50}')
    await finalize_injection(hub, connect_task)

    # Validate the Hub's state
    assert len(hub._devices) == 1, f"Expected 1 device, got {len(hub._devices)}"

    # Validate that the device has the metric we published
    device = list(hub._devices.values())[0]
    metric = device.get_metric_from_unique_id("123_system_0_system_ac_power_set_point")
    assert metric is not None, "Metric should exist in the device"
    assert isinstance(metric, Switch), f"Expected metric to be of type Switch, got {type(metric)}"
    assert metric.value == 50, f"Expected metric value to be 50, got {metric.value}"
    assert metric.min_value == -1000000, f"Expected metric min to be -1000000, got {metric.min_value}"
    assert metric.max_value == 1000000, f"Expected metric max to be 1000000, got {metric.max_value}"

@pytest.mark.asyncio
async def test_number_message(create_mocked_hub):
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub, connect_task = await create_mocked_hub

    # Inject messages after the event is set
    inject_message(hub, "N/123/evcharger/170/SetCurrent", "{\"value\": 100}")

    # Validate the Hub's state
    assert len(hub._devices) == 1, f"Expected 1 device, got {len(hub._devices)}"

    # Validate that the device has the metric we published
    device = list(hub._devices.values())[0]
    switch = device.get_metric_from_unique_id("123_evcharger_170_evcharger_set_current")
    assert isinstance(switch, Switch), f"Expected switch to be of type Switch, got {type(switch)}"
    assert switch.value == 100, f"Expected switch value to be 100, got {switch.value}"

    # Patch the publish method to track calls
    published = {}
    def mock_publish(topic, value):
        published['topic'] = topic
        published['value'] = value
        # Call the original publish if needed
        if hasattr(hub.publish, '__wrapped__'):
            return hub.publish.__wrapped__(topic, value)
    orig_publish = hub.publish
    hub.publish = mock_publish

    # Set the value, which should trigger a publish
    switch.value = 42

    # Validate that publish was called with the correct topic and value
    assert published, "Expected publish to be called after setting value"
    assert published['topic'] == "W/123/evcharger/170/SetCurrent", f"Expected topic 'W/123/evcharger/170/SetCurrent', got {published['topic']}"
    assert published['value'] == '{"value": 42}', f"Expected published value to be {'{"value": 42}'}, got {published['value']}"

    # Restore the original publish method
    hub.publish = orig_publish

    await finalize_injection(hub, connect_task)


@pytest.mark.asyncio
async def test_placeholder_adjustable_on(create_mocked_hub):
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub, connect_task = await create_mocked_hub

    # Inject messages after the event is set
    inject_message(hub, "N/123/vebus/170/Ac/ActiveIn/CurrentLimit", "{\"value\": 100}")
    inject_message(hub, "N/123/vebus/170/Ac/ActiveIn/CurrentLimitIsAdjustable", "{\"value\": 1}")
    await finalize_injection(hub, connect_task)

    # Validate the Hub's state
    assert len(hub._devices) == 1, f"Expected 1 device, got {len(hub._devices)}"

    # Validate that the device has the metric we published
    device = list(hub._devices.values())[0]
    assert len(device._metrics) == 1, f"Expected 1 metrics, got {len(device._metrics)}"
    metric = device.get_metric_from_unique_id("123_vebus_170_inverter_current_limit")
    assert isinstance(metric, Switch), f"Expected metric to be of type Switch, got {type(metric)}"
    assert metric is not None, "Metric should exist in the device"
    assert metric.value == 100, f"Expected metric value to be 100, got {metric.value}"
    # Ensure cleanup happens even if the test fails

@pytest.mark.asyncio
async def test_placeholder_adjustable_off(create_mocked_hub):
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub, connect_task = await create_mocked_hub

    # Inject messages after the event is set
    inject_message(hub, "N/123/vebus/170/Ac/ActiveIn/CurrentLimit", "{\"value\": 100}")
    inject_message(hub, "N/123/vebus/170/Ac/ActiveIn/CurrentLimitIsAdjustable", "{\"value\": 0}")
    await finalize_injection(hub, connect_task)

    # Validate the Hub's state
    assert len(hub._devices) == 1, f"Expected 1 device, got {len(hub._devices)}"

    # Validate that the device has the metric we published
    device = list(hub._devices.values())[0]
    assert len(device._metrics) == 1, f"Expected 1 metrics, got {len(device._metrics)}"
    metric = device.get_metric_from_unique_id("123_vebus_170_inverter_current_limit")
    assert not isinstance(metric, Switch), f"Expected metric to be of type Metric, got {type(metric)}"
    assert metric is not None, "Metric should exist in the device"
    assert metric.value == 100, f"Expected metric value to be 100, got {metric.value}"
    # Ensure cleanup happens even if the test fails

@pytest.mark.asyncio
async def test_placeholder_adjustable_on_reverse(create_mocked_hub):
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub, connect_task = await create_mocked_hub

    # Inject messages after the event is set
    inject_message(hub, "N/123/vebus/170/Ac/ActiveIn/CurrentLimitIsAdjustable", "{\"value\": 1}")
    inject_message(hub, "N/123/vebus/170/Ac/ActiveIn/CurrentLimit", "{\"value\": 100}")
    await finalize_injection(hub, connect_task)

    # Validate the Hub's state
    assert len(hub._devices) == 1, f"Expected 1 device, got {len(hub._devices)}"

    # Validate that the device has the metric we published
    device = list(hub._devices.values())[0]
    assert len(device._metrics) == 1, f"Expected 1 metrics, got {len(device._metrics)}"
    metric = device.get_metric_from_unique_id("123_vebus_170_inverter_current_limit")
    assert isinstance(metric, Switch), f"Expected metric to be of type Switch, got {type(metric)}"
    assert metric is not None, "Metric should exist in the device"
    assert metric.value == 100, f"Expected metric value to be 100, got {metric.value}"
    # Ensure cleanup happens even if the test fails

@pytest.mark.asyncio
async def test_placeholder_adjustable_off_reverse(create_mocked_hub):
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub, connect_task = await create_mocked_hub

    # Inject messages after the event is set
    inject_message(hub, "N/123/vebus/170/Ac/ActiveIn/CurrentLimitIsAdjustable", "{\"value\": 0}")
    inject_message(hub, "N/123/vebus/170/Ac/ActiveIn/CurrentLimit", "{\"value\": 100}")
    await finalize_injection(hub, connect_task)

    # Validate the Hub's state
    assert len(hub._devices) == 1, f"Expected 1 device, got {len(hub._devices)}"

    # Validate that the device has the metric we published
    device = list(hub._devices.values())[0]
    assert len(device._metrics) == 1, f"Expected 1 metrics, got {len(device._metrics)}"
    metric = device.get_metric_from_unique_id("123_vebus_170_inverter_current_limit")
    assert not isinstance(metric, Switch), f"Expected metric to be of type Metric, got {type(metric)}"
    assert metric is not None, "Metric should exist in the device"
    assert metric.value == 100, f"Expected metric value to be 100, got {metric.value}"
    # Ensure cleanup happens even if the test fails


@pytest.mark.asyncio
async def test_today_message(create_mocked_hub):
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub, connect_task = await create_mocked_hub

    # Inject messages after the event is set
    inject_message(hub, "N/123/solarcharger/290/History/Daily/0/MaxPower", "{\"value\": 1}")
    inject_message(hub, "N/123/solarcharger/290/History/Daily/1/MaxPower", "{\"value\": 2}")
    await finalize_injection(hub, connect_task)

    # Validate the Hub's state
    assert len(hub._devices) == 1, f"Expected 1 device, got {len(hub._devices)}"

    # Validate that the device has the metric we published
    device = list(hub._devices.values())[0]
    assert len(device._metrics) == 2, f"Expected 2 metrics, got {len(device._metrics)}"

    metric = device.get_metric_from_unique_id("123_solarcharger_290_solarcharger_max_power_today")
    assert metric is not None, "Metric should exist in the device"
    assert metric.value == 1, f"Expected metric value to be 1, got {metric.value}"

    metric = device.get_metric_from_unique_id("123_solarcharger_290_solarcharger_max_power_yesterday")
    assert metric is not None, "Metric should exist in the device"
    assert metric.value == 2, f"Expected metric value to be 2, got {metric.value}"

def test_expend_topics():
    descriptor = next((t for t in topics if t.topic == "N/+/switch/+/SwitchableOutput/output_{output(1-4)}/State"), None)
    assert descriptor is not None, "TopicDescriptor with the specified topic not found"

    expanded = Hub.expand_topic_list([descriptor])
    assert len(expanded) == 4, f"Expected 4 expanded topics, got {len(expanded)}"
    new_desc = next((t for t in expanded if t.topic == "N/+/switch/+/SwitchableOutput/output_1/State"), None)
    assert new_desc, "Missing expanded topic for output 1"
    assert new_desc.short_id == "switch_{output}_state"
    assert new_desc.name == "Switch {output} State"
    assert new_desc.key_values["output"] == "1"

@pytest.mark.asyncio
async def test_expend_message(create_mocked_hub):
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub, connect_task = await create_mocked_hub

    # Inject messages after the event is set
    inject_message(hub, "N/123/switch/170/SwitchableOutput/output_2/State", "{\"value\": 1}")
    await finalize_injection(hub, connect_task)

    # Validate the Hub's state
    assert len(hub._devices) == 1, f"Expected 1 device, got {len(hub._devices)}"

    # Validate that the device has the metric we published
    device = list(hub._devices.values())[0]
    metric = device.get_metric_from_unique_id("123_switch_170_switch_2_state")
    assert metric is not None, "Metric should exist in the device"
    assert metric.generic_short_id == "switch_{output}_state"
    assert metric.key_values["output"] == "2"
    assert metric.value == GenericOnOff.On, f"Expected metric value to be GenericOnOff.On, got {metric.value}"

@pytest.mark.asyncio
async def test_same_message_events(create_mocked_hub):
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub, connect_task = await create_mocked_hub

    # Inject messages after the event is set
    inject_message(hub, "N/123/grid/30/Ac/L1/Energy/Forward", "{\"value\": 42}")
    await finalize_injection(hub, connect_task, False)

    # Validate the Hub's state
    assert len(hub._devices) == 1, f"Expected 1 device, got {len(hub._devices)}"

    # Validate that the device has the metric we published
    device = list(hub._devices.values())[0]
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

    hub.disconnect()

@pytest.mark.asyncio
async def test_existing_installation_id(create_mocked_hub_with_installation_id):
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub, connect_task = await create_mocked_hub_with_installation_id

    # Inject messages after the event is set
    inject_message(hub, "N/123/switch/170/SwitchableOutput/output_2/State", "{\"value\": 1}")
    await finalize_injection(hub, connect_task)

    # Validate the Hub's state
    assert len(hub._devices) == 1, f"Expected 1 device, got {len(hub._devices)}"

    # Validate that the device has the metric we published
    device = list(hub._devices.values())[0]
    metric = device.get_metric_from_unique_id("123_switch_170_switch_2_state")
    assert metric is not None, "Metric should exist in the device"
    assert metric.generic_short_id == "switch_{output}_state"
    assert metric.key_values["output"] == "2"
    assert metric.value == GenericOnOff.On, f"Expected metric value to be GenericOnOff.On, got {metric.value}"


@pytest.mark.asyncio
async def test_multiple_hubs(create_mocked_hub_with_installation_id, create_mocked_hub):
    """Test that the Hub correctly updates its internal state based on MQTT messages."""
    hub1, connect_task1 = await create_mocked_hub

    # Inject messages after the event is set
    inject_message(hub1, "N/123/switch/170/SwitchableOutput/output_2/State", "{\"value\": 1}")
    await finalize_injection(hub1, connect_task1, disconnect=False)

    # Validate the Hub's state
    assert len(hub1._devices) == 1, f"Expected 1 device, got {len(hub1._devices)}"

    # Validate that the device has the metric we published
    device1 = list(hub1._devices.values())[0]
    metric1 = device1.get_metric_from_unique_id("123_switch_170_switch_2_state")
    assert metric1 is not None, "Metric should exist in the device"
    assert metric1.generic_short_id == "switch_{output}_state"
    assert metric1.key_values["output"] == "2"
    assert metric1.value == GenericOnOff.On, f"Expected metric value to be GenericOnOff.On, got {metric1.value}"

    hub2, connect_task2 = await create_mocked_hub_with_installation_id
    # Inject messages after the event is set
    inject_message(hub2, "N/123/switch/170/SwitchableOutput/output_2/State", "{\"value\": 0}")
    await finalize_injection(hub1, connect_task1, disconnect=False)

    # Validate the Hub's state
    assert len(hub2._devices) == 1, f"Expected 1 device, got {len(hub1._devices)}"

    # Validate that the device has the metric we published
    device2 = list(hub2._devices.values())[0]
    metric2 = device2.get_metric_from_unique_id("123_switch_170_switch_2_state")
    assert metric2 is not None, "Metric should exist in the device"
    assert metric2.generic_short_id == "switch_{output}_state"
    assert metric2.key_values["output"] == "2"
    assert metric2.value == GenericOnOff.Off, f"Expected metric value to be GenericOnOff.Off, got {metric2.value}"
