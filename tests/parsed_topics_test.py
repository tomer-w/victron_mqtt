"""Unit tests for the ParsedTopic class and its interaction with TopicDescriptor, including handling of topics with placeholders and device type mapping."""
import pytest

from victron_mqtt._victron_enums import DeviceType, GenericOnOff
from victron_mqtt.constants import MetricKind, MetricNature, MetricType, ValueType, VictronEnum
from victron_mqtt.data_classes import ParsedTopic, TopicDescriptor, topic_to_device_type
from victron_mqtt._victron_topics import topics

def test_parsed_topic_with_pattern():
    """Test parsing a topic that includes a placeholder and ensure it is correctly extracted and matched to the TopicDescriptor."""
    # Find the TopicDescriptor with the desired topic
    descriptor = next((t for t in topics if t.topic == "N/{installation_id}/system/{device_id}/Relay/{relay}/State"), None)
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
    assert parsed_topic.short_id == "system_relay_1", "Short ID should match"


def test_parsed_topic_with_phase():
    """Test parsing a topic that includes a phase placeholder and ensure it is correctly extracted and matched to the TopicDescriptor."""
    # Find the TopicDescriptor with the desired topic
    descriptor = next((t for t in topics if t.topic == "N/{installation_id}/system/{device_id}/Ac/Genset/{phase}/Power"), None)
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
    assert parsed_topic.short_id == "system_generator_load_l1", "Short ID should match"

def test_parsed_topic_with_next_phase():
    """Test parsing a topic that includes a phase placeholder and ensure it is correctly extracted and matched to the TopicDescriptor."""
    # Find the TopicDescriptor with the desired topic
    descriptor = next((t for t in topics if t.topic == "N/{installation_id}/grid/{device_id}/Ac/{phase}/VoltageLineToLine"), None)
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
    assert parsed_topic.short_id == "grid_voltage_l3_l1", "Short ID should match"

def test_parsed_topic_with_phase_and_placeholder():
    """Test parsing a topic that includes a phase placeholder and another placeholder, and ensure they are correctly extracted and matched to the TopicDescriptor."""
    # Find the TopicDescriptor with the desired topic
    descriptor = next((t for t in topics if t.topic == "N/{installation_id}/multi/{device_id}/Ac/Out/{output}/{phase}/I"), None)
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
    assert parsed_topic.short_id == "multi_acout_1_current_l1", "Short ID should match"

def test_settings_parsed_topic():
    """Test parsing a settings topic and ensure it is correctly extracted and matched to the TopicDescriptor, including handling of device type mapping."""
    # Find the TopicDescriptor with the desired topic
    descriptor = next((t for t in topics if t.topic == "N/{installation_id}/settings/{device_id}/Settings/CGwacs/AcPowerSetPoint"), None)
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
    assert parsed_topic.short_id == "system_ac_power_set_point", "Short ID should match"


def test_settings_parsed_topic_2():
    """Test parsing a settings topic for a different device type and ensure it is correctly extracted and matched to the TopicDescriptor, including handling of device type mapping."""
    # Find the TopicDescriptor with the desired topic
    descriptor = next((t for t in topics if t.topic == "N/{installation_id}/settings/{device_id}/Settings/SystemSetup/MaxChargeCurrent"), None)
    assert descriptor is not None, "TopicDescriptor with the specified topic not found"

    # Create a ParsedTopic instance
    topic = "N/061c6f611bd7/settings/0/Settings/SystemSetup/MaxChargeCurrent"
    parsed_topic = ParsedTopic.from_topic(topic)
    assert parsed_topic is not None, "ParsedTopic should not be None"

    # Validate the ParsedTopic instance
    assert parsed_topic.installation_id == "061c6f611bd7", "Installation ID should match"
    assert parsed_topic.device_id == "0", "Device ID should match"
    assert parsed_topic.device_type == DeviceType.SYSTEM_SETUP # We decided that SYSTEM_SETUP will not be mapped

    parsed_topic.finalize_topic_fields(descriptor)
    # Validate the ParsedTopic instance additional fields after matching description
    assert parsed_topic.short_id == "system_ess_max_charge_current", "Short ID should match"

def test_parsed_root_topic():
    """Test parsing a root topic that does not include a device_id placeholder and ensure it is correctly extracted and matched to the TopicDescriptor, including handling of device type mapping."""
    # Find the TopicDescriptor with the desired topic
    descriptor = next((t for t in topics if t.topic == "N/{installation_id}/heartbeat"), None)
    assert descriptor is not None, "TopicDescriptor with the specified topic not found"

    # Create a ParsedTopic instance
    topic = "N/123/heartbeat"
    parsed_topic = ParsedTopic.from_topic(topic)
    assert parsed_topic is not None, "ParsedTopic should not be None"

    # Validate the ParsedTopic instance
    assert parsed_topic.installation_id == "123", "Installation ID should match"
    assert parsed_topic.device_id == "0", "Device ID should always be 0 for root topics"
    assert parsed_topic.device_type == DeviceType.SYSTEM, "Device type should always be SYSTEM for root topics"

    parsed_topic.finalize_topic_fields(descriptor)
    # Validate the ParsedTopic instance additional fields after matching description
    assert parsed_topic.short_id == "system_heartbeat", "Short ID should match"


class TestVictronEnumFromString:
    """Test from_string error path (lines 129-130)."""

    def test_invalid_string_raises(self):
        with pytest.raises(ValueError, match="No enum member found"):
            GenericOnOff.from_string("NonExistent")


class TestVictronDeviceEnumMapped:
    """Test VictronDeviceEnum mapped_to path (line 148)."""

    def test_mapped_device_type(self):
        # Find a device type that has mapped_to set
        for member in DeviceType:
            if member.mapped_to:
                result = DeviceType.from_code(member.code)
                assert result is not None
                assert result.mapped_to is None  # Should resolve to the target
                break

    def test_unknown_code_returns_none(self):
        result = DeviceType.from_code("nonexistent_device_type")
        assert result is None


class TestTopicToDeviceType:
    """Test topic_to_device_type edge cases (line 23)."""

    def test_short_topic(self):
        result = topic_to_device_type(["N"])
        assert result is None


class TestParsedTopic:
    """Test ParsedTopic methods (lines 235, 256-259, 349, 374, 378)."""

    def test_hash(self):
        pt = ParsedTopic.from_topic("N/123/battery/0/Soc")
        assert pt is not None
        assert isinstance(hash(pt), int)

    def test_short_topic_returns_none(self):
        result = ParsedTopic.from_topic("N/123")
        assert result is None

    def test_three_parts_non_heartbeat(self):
        result = ParsedTopic.from_topic("N/123/unknown")
        assert result is None

    def test_next_phase_l2(self):
        assert ParsedTopic._get_next_phase("L2") == "L3"

    def test_next_phase_l3(self):
        assert ParsedTopic._get_next_phase("L3") == "L1"

    def test_next_phase_invalid(self):
        with pytest.raises(ValueError, match="Invalid phase"):
            ParsedTopic._get_next_phase("L4")

    def test_replace_ids_no_match(self):
        result = ParsedTopic.replace_ids("no placeholders here", {})
        assert result == "no placeholders here"

    def test_replace_ids_with_match(self):
        result = ParsedTopic.replace_ids("device {device_id} metric", {"device_id": "42"})
        assert result == "device 42 metric"

    def test_replace_ids_unmatched_placeholder(self):
        result = ParsedTopic.replace_ids("{unknown}", {})
        assert result == "{unknown}"


class TestTopicDescriptorPostInit:
    """Test TopicDescriptor __post_init__ defaults (lines 169, 171)."""

    def test_time_metric_defaults(self):
        desc = TopicDescriptor(
            topic="N/{installation_id}/system/{device_id}/Time",
            message_type=MetricKind.SENSOR,
            short_id="test_time",
            name="Test Time",
            metric_type=MetricType.TIME,
        )
        assert desc.unit_of_measurement == "s"
        assert desc.value_type == ValueType.INT
        assert desc.metric_nature == MetricNature.INSTANTANEOUS
        # Note: precision is reset to None by __post_init__ for non-float types
        assert desc.precision is None
        assert desc.min == 0
        assert desc.max == 86400
