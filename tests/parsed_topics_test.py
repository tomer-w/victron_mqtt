from victron_mqtt._victron_enums import DeviceType
from victron_mqtt.data_classes import ParsedTopic
from victron_mqtt._victron_topics import topics

def test_parsed_topic_with_pattern():
    # Find the TopicDescriptor with the desired topic
    descriptor = next((t for t in topics if t.topic == "N/+/system/+/Relay/{relay}/State"), None)
    assert descriptor is not None, "TopicDescriptor with the specified topic not found"

    # Create a ParsedTopic instance
    topic = "N/123/system/456/Relay/1/State"
    parsed_topic = ParsedTopic.from_topic(topic)
    assert parsed_topic is not None, "ParsedTopic should not be None"

    # Validate the ParsedTopic instance
    assert parsed_topic.installation_id == "123", "Installation ID should match"
    assert parsed_topic.device_id == "456", "Device ID should match"
    assert parsed_topic.device_type == DeviceType.SYSTEM, "Device type should match"

    parsed_topic.finalize_topic_fields(descriptor)
    # Validate the ParsedTopic instance additional fields after matching description
    assert parsed_topic.key_values["relay"] == "1", "Relay ID should match"
    assert parsed_topic.name == "Relay 1 state", "Name should match"
    assert parsed_topic.short_id == "system_relay_1", "Short ID should match"


def test_parsed_topic_with_phase():
    # Find the TopicDescriptor with the desired topic
    descriptor = next((t for t in topics if t.topic == "N/+/system/+/Ac/Genset/{phase}/Power"), None)
    assert descriptor is not None, "TopicDescriptor with the specified topic not found"

    # Create a ParsedTopic instance
    topic = "N/123/system/456/Ac/Genset/L1/Power"
    parsed_topic = ParsedTopic.from_topic(topic)
    assert parsed_topic is not None, "ParsedTopic should not be None"

    # Validate the ParsedTopic instance
    assert parsed_topic.installation_id == "123", "Installation ID should match"
    assert parsed_topic.device_id == "456", "Device ID should match"
    assert parsed_topic.device_type == DeviceType.SYSTEM, "Device type should match"

    parsed_topic.finalize_topic_fields(descriptor)
    # Validate the ParsedTopic instance additional fields after matching description
    assert parsed_topic.key_values["phase"] == "L1", "Phase should match"
    assert parsed_topic.name == "Genset Load L1", "Name should match"
    assert parsed_topic.short_id == "system_generator_load_L1", "Short ID should match"

def test_parsed_topic_with_next_phase():
    # Find the TopicDescriptor with the desired topic
    descriptor = next((t for t in topics if t.topic == "N/+/grid/+/Ac/{phase}/VoltageLineToLine"), None)
    assert descriptor is not None, "TopicDescriptor with the specified topic not found"

    # Create a ParsedTopic instance
    topic = "N/123/grid/456/Ac/L3/VoltageLineToLine"
    parsed_topic = ParsedTopic.from_topic(topic)
    assert parsed_topic is not None, "ParsedTopic should not be None"

    # Validate the ParsedTopic instance
    assert parsed_topic.installation_id == "123", "Installation ID should match"
    assert parsed_topic.device_id == "456", "Device ID should match"
    assert parsed_topic.device_type == DeviceType.GRID, "Device type should match"

    parsed_topic.finalize_topic_fields(descriptor)
    # Validate the ParsedTopic instance additional fields after matching description
    assert parsed_topic.key_values["phase"] == "L3", "Phase should match"
    assert parsed_topic.name == "Grid voltage L3 to L1", "Name should match"
    assert parsed_topic.short_id == "grid_voltage_L3_L1", "Short ID should match"

def test_parsed_topic_with_phase_and_placeholder():
    # Find the TopicDescriptor with the desired topic
    descriptor = next((t for t in topics if t.topic == "N/+/multi/+/Ac/Out/{output}/{phase}/I"), None)
    assert descriptor is not None, "TopicDescriptor with the specified topic not found"

    # Create a ParsedTopic instance
    topic = "N/123/multi/456/Ac/Out/1/L1/I"
    parsed_topic = ParsedTopic.from_topic(topic)
    assert parsed_topic is not None, "ParsedTopic should not be None"

    # Validate the ParsedTopic instance
    assert parsed_topic.installation_id == "123", "Installation ID should match"
    assert parsed_topic.device_id == "456", "Device ID should match"
    assert parsed_topic.device_type == DeviceType.MULTI_RS_SOLAR, "Device type should match"

    parsed_topic.finalize_topic_fields(descriptor)
    # Validate the ParsedTopic instance additional fields after matching description
    assert parsed_topic.key_values["phase"] == "L1", "Phase should match"
    assert parsed_topic.name == "AC Out 1 Current on L1", "Name should match"
    assert parsed_topic.short_id == "multirssolar_acout_1_current_L1", "Short ID should match"

def test_settings_parsed_topic():
    # Find the TopicDescriptor with the desired topic
    descriptor = next((t for t in topics if t.topic == "N/+/settings/+/Settings/CGwacs/AcPowerSetPoint"), None)
    assert descriptor is not None, "TopicDescriptor with the specified topic not found"

    # Create a ParsedTopic instance
    topic = "N/123/settings/0/Settings/CGwacs/AcPowerSetPoint"
    parsed_topic = ParsedTopic.from_topic(topic)
    assert parsed_topic is not None, "ParsedTopic should not be None"

    # Validate the ParsedTopic instance
    assert parsed_topic.installation_id == "123", "Installation ID should match"
    assert parsed_topic.device_id == "0", "Device ID should match"
    assert parsed_topic.device_type == DeviceType.SYSTEM # We decided to map CGwacs to SYSTEM

    parsed_topic.finalize_topic_fields(descriptor)
    # Validate the ParsedTopic instance additional fields after matching description
    assert parsed_topic.name == "AC Power Setpoint", "Name should match"
    assert parsed_topic.short_id == "system_ac_power_set_point", "Short ID should match"
