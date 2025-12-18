"""Tests basic connectivity functionality. Does require a running Venus OS instance to connect to."""

import pytest

def get_topics():
    from victron_mqtt._victron_topics import topics
    return topics

def get_metric_kind():
    from victron_mqtt.constants import MetricKind
    return MetricKind

def get_value_type():
    from victron_mqtt.constants import ValueType
    return ValueType

def get_metric_type():
    from victron_mqtt.constants import MetricType
    return MetricType

def get_metric_nature():
    from victron_mqtt.constants import MetricNature
    return MetricNature

def test_no_duplicate_short_ids():
    topics = get_topics()
    MetricKind = get_metric_kind()
    short_ids = {}
    errors = []
    for descriptor in topics:
        if descriptor.message_type != MetricKind.ATTRIBUTE:
            short_id = descriptor.short_id
            if short_id in short_ids:
                errors.append(f"Duplicate short_id '{short_id}' found in topics: '{descriptor.topic}' and '{short_ids[short_id]}'")
            short_ids[short_id] = descriptor.topic
    if errors:
        pytest.fail("\n".join(errors))

def test_no_duplicate_device_type_and_name():
    topics = get_topics()
    MetricKind = get_metric_kind()
    from victron_mqtt.data_classes import topic_to_device_type
    names = {}
    errors = []
    for descriptor in topics:
        if descriptor.message_type != MetricKind.ATTRIBUTE:
            name = f"devicetype '{topic_to_device_type(descriptor.topic.split('/'))}' name '{descriptor.name}'"
            if name in names:
                errors.append(f"Duplicate {name} found in topics: '{descriptor.topic}' and '{names[name]}'")
            names[name] = descriptor.topic
    if errors:
        pytest.fail("\n".join(errors))

def test_naming_unit_consistency():
    topics = get_topics()
    MetricType = get_metric_type()
    errors = []
    for descriptor in topics:
        if descriptor.name and descriptor.unit_of_measurement:
            if descriptor.unit_of_measurement == "VA" and "frequency" in descriptor.name.lower():
                errors.append(f"Unit mismatch: topic '{descriptor.topic}' has unit 'VA' but name suggests frequency: '{descriptor.name}'")
            if descriptor.unit_of_measurement == "%" and descriptor.metric_type not in [MetricType.PERCENTAGE, MetricType.ELECTRIC_STORAGE_PERCENTAGE]:
                errors.append(f"Unit/type mismatch: topic '{descriptor.topic}' has unit '%' but metric_type is {descriptor.metric_type}")
    if errors:
        pytest.fail("\n".join(errors))

def test_required_fields_for_sensor():
    topics = get_topics()
    MetricKind = get_metric_kind()
    ValueType = get_value_type()
    MetricNature = get_metric_nature()
    errors = []
    for descriptor in topics:
        if descriptor.message_type == MetricKind.SENSOR:
            if descriptor.name is None:
                errors.append(f"SENSOR topic '{descriptor.topic}' missing required 'name' field")
            if descriptor.value_type is None:
                errors.append(f"SENSOR topic '{descriptor.topic}' missing required 'value_type' field")
        if descriptor.value_type in [ValueType.STRING, ValueType.ENUM, ValueType.BITMASK] and descriptor.precision is not None:
            errors.append(f"Topic '{descriptor.topic}' has value_type {descriptor.value_type} but also has precision={descriptor.precision} (should be None)")
        if descriptor.value_type == ValueType.ENUM and descriptor.enum is None:
            errors.append(f"Topic '{descriptor.topic}' has value_type ENUM but missing 'enum' field")
        if descriptor.value_type == ValueType.ENUM and descriptor.metric_nature != MetricNature.NONE:
            errors.append(f"Topic '{descriptor.topic}' has value_type ENUM but metric_nature is {descriptor.metric_nature} (should be NONE)")
        if descriptor.value_type == ValueType.BITMASK and descriptor.enum is None:
            errors.append(f"Topic '{descriptor.topic}' has value_type BITMASK but missing 'enum' field")
        if descriptor.value_type == ValueType.BITMASK and descriptor.metric_nature != MetricNature.NONE:
            errors.append(f"Topic '{descriptor.topic}' has value_type BITMASK but metric_nature is {descriptor.metric_nature} (should be NONE)")
        if descriptor.value_type not in [ValueType.ENUM, ValueType.BITMASK] and descriptor.enum is not None:
            errors.append(f"Topic '{descriptor.topic}' has 'enum' field but value_type is not ENUM")
    if errors:
        pytest.fail("\n".join(errors))

def test_enum_message_type():
    topics = get_topics()
    MetricKind = get_metric_kind()
    from victron_mqtt._victron_enums import GenericOnOff
    errors = []
    for descriptor in topics:
        if descriptor.enum is not None:
            if descriptor.enum == GenericOnOff and descriptor.message_type == MetricKind.BINARY_SENSOR:
                continue
            if descriptor.message_type not in [MetricKind.SELECT, MetricKind.SENSOR, MetricKind.SWITCH, MetricKind.BUTTON]:
                errors.append(f"Topic '{descriptor.topic}' has 'enum' but message_type is {descriptor.message_type} (should be SELECT, SENSOR, SWITCH, BUTTON, or BINARY_SENSOR for GenericOnOff)")
    if errors:
        pytest.fail("\n".join(errors))

def test_short_id_format():
    topics = get_topics()
    import re
    short_id_pattern = re.compile(r'^[a-z0-9_-]+(?:\{[a-z_]+\}[a-z0-9_-]*)*$')
    errors = []
    for descriptor in topics:
        short_id = descriptor.short_id
        if short_id:
            if not short_id_pattern.match(short_id):
                errors.append(f"Topic '{descriptor.topic}' has invalid short_id '{short_id}' (must contain only lowercase letters, numbers, hyphens, underscores, and {{placeholders}})")
            if short_id.startswith('_'):
                errors.append(f"Topic '{descriptor.topic}' has short_id '{short_id}' that starts with underscore (not allowed)")
            if short_id.endswith('_'):
                errors.append(f"Topic '{descriptor.topic}' has short_id '{short_id}' that ends with underscore (not allowed)")
    if errors:
        pytest.fail("\n".join(errors))

def test_metric_type_vs_unit():
    topics = get_topics()
    MetricType = get_metric_type()
    errors = []
    for descriptor in topics:
        if descriptor.unit_of_measurement == "°C" and descriptor.metric_type != MetricType.TEMPERATURE:
            errors.append(f"Topic '{descriptor.topic}' has temperature unit '°C' but metric_type is {descriptor.metric_type}")
        if descriptor.unit_of_measurement == "V" and descriptor.metric_type != MetricType.VOLTAGE:
            errors.append(f"Topic '{descriptor.topic}' has voltage unit 'V' but metric_type is {descriptor.metric_type}")
        if descriptor.unit_of_measurement == "A" and descriptor.metric_type != MetricType.CURRENT:
            errors.append(f"Topic '{descriptor.topic}' has current unit 'A' but metric_type is {descriptor.metric_type}")
        if descriptor.unit_of_measurement == "W" and descriptor.metric_type != MetricType.POWER:
            errors.append(f"Topic '{descriptor.topic}' has power unit 'W' but metric_type is {descriptor.metric_type}")
        if descriptor.unit_of_measurement == "Hz" and descriptor.metric_type != MetricType.FREQUENCY:
            errors.append(f"Topic '{descriptor.topic}' has frequency unit 'Hz' but metric_type is {descriptor.metric_type}")
        if descriptor.unit_of_measurement == "kWh" and descriptor.metric_type != MetricType.ENERGY:
            errors.append(f"Topic '{descriptor.topic}' has energy unit 'kWh' but metric_type is {descriptor.metric_type}")
        if descriptor.unit_of_measurement in ["s", "min", "h"] and (descriptor.metric_type != MetricType.TIME and descriptor.metric_type != MetricType.DURATION):
            errors.append(f"Topic '{descriptor.topic}' has time unit '{descriptor.unit_of_measurement}' but metric_type is {descriptor.metric_type}")
    if errors:
        pytest.fail("\n".join(errors))

def test_metric_nature_for_energy_and_power():
    topics = get_topics()
    MetricType = get_metric_type()
    MetricNature = get_metric_nature()
    errors = []
    for descriptor in topics:
        if descriptor.metric_type == MetricType.ENERGY and descriptor.metric_nature != MetricNature.CUMULATIVE:
            errors.append(f"Topic '{descriptor.topic}' has metric_type ENERGY but metric_nature is {descriptor.metric_nature} (should be CUMULATIVE)")
        if descriptor.metric_type == MetricType.POWER and descriptor.metric_nature not in [MetricNature.INSTANTANEOUS, MetricNature.NONE]:
            errors.append(f"Topic '{descriptor.topic}' has metric_type POWER but metric_nature is {descriptor.metric_nature} (should be INSTANTANEOUS)")
    if errors:
        pytest.fail("\n".join(errors))

def test_topic_pattern_structure():
    topics = get_topics()
    MetricKind = get_metric_kind()
    errors = []
    for descriptor in topics:
        topic = descriptor.topic
        # Skip formula topics which have special structure
        if topic.startswith('$$func'):
            topic_parts = topic.split('/')
            if len(topic_parts) < 3:
                errors.append(f"Topic '{topic}' has invalid structure (too few parts)")
            continue
        topic_parts = topic.split('/')
        if len(topic_parts) < 3:
            errors.append(f"Topic '{topic}' has invalid structure (too few parts)")
        if descriptor.message_type != MetricKind.SERVICE and descriptor.message_type != MetricKind.BUTTON and not topic.startswith('N/{installation_id}/'):
            errors.append(f"Topic '{topic}' must start with 'N{{installation_id}}/'")
        elif descriptor.message_type == MetricKind.SERVICE and not topic.startswith('W/{installation_id}/'):
            errors.append(f"Service topic '{topic}' must start with 'W{{installation_id}}/'")
        if not topic.find('N/{device_id}/') == -1 and len(topic_parts) > 3:
            errors.append(f"Topic '{topic}' must include 'N{{device_id}}/'")
    if errors:
        pytest.fail("\n".join(errors))

def test_phase_placeholder_for_plus_topics():
    topics = get_topics()
    MetricKind = get_metric_kind()
    errors = []
    for descriptor in topics:
        topic = descriptor.topic
        plus_count = topic.count('+')
        if plus_count == 3 and descriptor.message_type != MetricKind.ATTRIBUTE:
            if descriptor.short_id and '{phase}' not in descriptor.short_id:
                errors.append(f"Topic '{topic}' has {plus_count} plus signs but short_id '{descriptor.short_id}' missing {{phase}} placeholder")
            if descriptor.name and '{phase}' not in descriptor.name:
                errors.append(f"Topic '{topic}' has {plus_count} plus signs but name '{descriptor.name}' missing {{phase}} placeholder")
    if errors:
        pytest.fail("\n".join(errors))

def test_no_literal_phase_identifiers():
    topics = get_topics()
    errors = []
    for descriptor in topics:
        topic = descriptor.topic
        topic_parts = topic.split('/')
        for part in topic_parts:
            if part in ['L1', 'L2', 'L3']:
                errors.append(f"Topic '{topic}' contains literal phase identifier '{part}' - use '+' placeholder instead")
    if errors:
        pytest.fail("\n".join(errors))

def test_no_invalid_double_slash():
    topics = get_topics()
    errors = []
    for descriptor in topics:
        if '//' in descriptor.topic:
            errors.append(f"Topic '{descriptor.topic}' contains invalid '//' sequence")
    if errors:
        pytest.fail("\n".join(errors))

def test_valid_device_type_in_topic():
    topics = get_topics()
    MetricKind = get_metric_kind()
    from victron_mqtt._victron_enums import DeviceType
    valid_device_types = {member.code for member in DeviceType}
    valid_device_types.add("Generator{gen_id(0-1)}")
    errors = []
    for descriptor in topics:
        if descriptor.message_type == MetricKind.ATTRIBUTE:
            continue
        topic_parts = descriptor.topic.split('/')
        if len(topic_parts) <= 2:
            errors.append(f"Topic '{descriptor.topic}' has invalid structure (too few parts)")
            continue
        if topic_parts[0] == "$$func":
            actual_device_type = topic_parts[1]
            if actual_device_type not in valid_device_types:
                errors.append(f"Formula topic '{descriptor.topic}' has invalid actual_device_type '{actual_device_type}' not defined in DeviceType")
            continue
        if len(topic_parts) == 3: # root topic without device_type
            continue
        device_type = topic_parts[2]
        if device_type != "settings" and device_type not in valid_device_types:
            errors.append(f"Topic '{descriptor.topic}' has invalid device_type '{device_type}' not defined in DeviceType")
        if len(topic_parts) > 5 and topic_parts[2] == 'settings':
            actual_device_type = topic_parts[5]
            if actual_device_type not in valid_device_types:
                errors.append(f"Settings topic '{descriptor.topic}' has invalid actual_device_type '{actual_device_type}' not defined in DeviceType")
    if errors:
        pytest.fail("\n".join(errors))

def test_no_installation_id_or_device_id_in_short_id_or_name():
    topics = get_topics()
    errors = []
    for descriptor in topics:
        if descriptor.short_id and ("{installation_id}" in descriptor.short_id or "{device_id}" in descriptor.short_id):
            errors.append(f"Topic '{descriptor.topic}' has short_id '{descriptor.short_id}' containing forbidden placeholder '{{installation_id}}' or '{{device_id}}'")
        if descriptor.name and ("{installation_id}" in descriptor.name or "{device_id}" in descriptor.name):
            errors.append(f"Topic '{descriptor.topic}' has name '{descriptor.name}' containing forbidden placeholder '{{installation_id}}' or '{{device_id}}'")
    if errors:
        pytest.fail("\n".join(errors))

def test_victron_enum_in_init():
    """Ensure all VictronEnum-derived enums are included in __init__.py's __all__."""
    from victron_mqtt.constants import VictronEnum
    from victron_mqtt import __all__

    # Collect all subclasses of VictronEnum
    victron_enum_classes = [cls.__name__ for cls in VictronEnum.__subclasses__()]

    # Check if all subclasses are in __all__
    missing_enums = [enum for enum in victron_enum_classes if enum not in __all__]

    assert not missing_enums, f"The following VictronEnum-derived enums are missing in __init__.py's __all__: {missing_enums}"

def test_topics_are_sorted_alphabetically():
    """Ensure TopicDescriptor entries are sorted alphabetically by topic field."""
    topics = get_topics()
    MetricKind = get_metric_kind()
    
    # Separate attributes from other topics
    attributes = [topic for topic in topics if topic.message_type == MetricKind.ATTRIBUTE]
    other_topics = [topic for topic in topics if topic.message_type != MetricKind.ATTRIBUTE and not topic.topic.startswith("$$func/")]
    
    errors = []
    
    # Check that attributes are sorted alphabetically
    if len(attributes) > 1:
        for i in range(1, len(attributes)):
            current_topic = attributes[i].topic
            previous_topic = attributes[i-1].topic
            if current_topic < previous_topic:
                errors.append(f"Attribute topics not in alphabetical order: '{previous_topic}' should come after '{current_topic}'")
    
    # Check that all other topics are sorted alphabetically
    if len(other_topics) > 1:
        for i in range(1, len(other_topics)):
            current_topic = other_topics[i].topic
            previous_topic = other_topics[i-1].topic
            if current_topic < previous_topic:
                errors.append(f"Topics not in alphabetical order: '{previous_topic}' should come after '{current_topic}'")
    
    if errors:
        pytest.fail("\n".join(errors))

def test_name_references_exist():
    """Test that when a topic name contains a reference like {key:short_id}, the referenced short_id exists."""
    topics = get_topics()
    errors = []
    
    # First collect all short_ids
    short_ids = {descriptor.short_id for descriptor in topics}
    
    # Check each topic's name for references
    for descriptor in topics:
        if descriptor.name:
            # Look for patterns like {key:short_id}
            import re
            references = re.findall(r'\{(?P<moniker>[^:]+:(?:[^{}]|{[^{}]*})+)\}', descriptor.name)
            for ref_short_id in references:
                ref = ref_short_id.split(":", 1)[1]
                if ref not in short_ids:
                    errors.append(f"Topic '{descriptor.topic}' name references non-existent short_id '{ref_short_id}' in name '{descriptor.name}'")
    
    if errors:
        pytest.fail("\n".join(errors))

