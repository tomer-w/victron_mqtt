"""Tests basic connectivity functionality. Does require a running Venus OS instance to connect to."""

import pytest

from victron_mqtt._victron_enums import GenericOnOff

def test_topics():
    """Tests the topics list for various mistakes and inconsistencies.
    
    This test validates:
    1. No duplicate short_ids (except for attributes)
    2. Proper unit/metric type matching
    3. Required fields for different message types
    4. Proper enum/value_type combinations
    5. Correct metric nature for energy/power types
    6. Valid topic structure patterns
    7. Valid short_id format (lowercase letters, numbers, hyphens, underscores, and placeholders; cannot start/end with underscore)
    """
    from victron_mqtt._victron_topics import topics
    from victron_mqtt.constants import MetricKind, ValueType, MetricType, MetricNature
    
    errors = []
    
    # Check for duplicate short_ids (except for attributes which can be duplicated)
    short_ids = {}
    for descriptor in topics:
        if descriptor.message_type != MetricKind.ATTRIBUTE:
            short_id = descriptor.short_id
            if short_id in short_ids:
                errors.append(f"Duplicate short_id '{short_id}' found in topics: '{descriptor.topic}' and '{short_ids[short_id]}'")
            else:
                short_ids[short_id] = descriptor.topic
    
    # Check for inconsistent naming patterns
    for descriptor in topics:        
        # Check for inconsistent name vs unit_of_measurement mismatch
        if descriptor.name and descriptor.unit_of_measurement:
            # Check for apparent power with wrong name
            if descriptor.unit_of_measurement == "VA" and "frequency" in descriptor.name.lower():
                errors.append(f"Unit mismatch: topic '{descriptor.topic}' has unit 'VA' but name suggests frequency: '{descriptor.name}'")
            
            # Check for percentage with wrong unit
            if descriptor.unit_of_measurement == "%" and descriptor.metric_type != MetricType.PERCENTAGE:
                errors.append(f"Unit/type mismatch: topic '{descriptor.topic}' has unit '%' but metric_type is {descriptor.metric_type}")
        
    # Check for missing required fields based on message_type
    for descriptor in topics:
        if descriptor.message_type == MetricKind.SENSOR:
            if descriptor.name is None:
                errors.append(f"SENSOR topic '{descriptor.topic}' missing required 'name' field")
            if descriptor.value_type is None:
                errors.append(f"SENSOR topic '{descriptor.topic}' missing required 'value_type' field")
        
        # Check for precision field consistency
        if descriptor.value_type in [ValueType.STRING, ValueType.ENUM] and descriptor.precision is not None:
            errors.append(f"Topic '{descriptor.topic}' has value_type {descriptor.value_type} but also has precision={descriptor.precision} (should be None)")
        
        # Check for enum field consistency  
        if descriptor.value_type == ValueType.ENUM and descriptor.enum is None:
            errors.append(f"Topic '{descriptor.topic}' has value_type ENUM but missing 'enum' field")
        if descriptor.value_type != ValueType.ENUM and descriptor.enum is not None:
            errors.append(f"Topic '{descriptor.topic}' has 'enum' field but value_type is not ENUM")
        
        # Check that ENUM value_type has NONE metric_nature
        if descriptor.value_type == ValueType.ENUM and descriptor.metric_nature != MetricNature.NONE:
            errors.append(f"Topic '{descriptor.topic}' has value_type ENUM but metric_nature is {descriptor.metric_nature} (should be NONE)")

    # Check that topics with 'enum' are of MetricKind.SELECT, MetricKind.SENSOR, or MetricKind.SWITCH
    # Allow MetricKind.BINARY_SENSOR only for GenericOnOff enum
    for descriptor in topics:
        if descriptor.enum is not None:
            if descriptor.enum == GenericOnOff and descriptor.message_type == MetricKind.BINARY_SENSOR:
                continue
            if descriptor.message_type not in [MetricKind.SELECT, MetricKind.SENSOR, MetricKind.SWITCH]:
                errors.append(f"Topic '{descriptor.topic}' has 'enum' but message_type is {descriptor.message_type} (should be SELECT, SENSOR, SWITCH, or BINARY_SENSOR for GenericOnOff)")

    # Check for valid short_id format
    import re
    short_id_pattern = re.compile(r'^[a-z0-9_-]+(?:\{[a-z_]+\}[a-z0-9_-]*)*$')
    for descriptor in topics:
        short_id = descriptor.short_id
        if short_id:
            # Check if short_id matches the allowed pattern (allowing placeholders like {phase})
            if not short_id_pattern.match(short_id):
                errors.append(f"Topic '{descriptor.topic}' has invalid short_id '{short_id}' (must contain only lowercase letters, numbers, hyphens, underscores, and {{placeholders}})")
            
            # Check if short_id starts or ends with underscore
            if short_id.startswith('_'):
                errors.append(f"Topic '{descriptor.topic}' has short_id '{short_id}' that starts with underscore (not allowed)")
            if short_id.endswith('_'):
                errors.append(f"Topic '{descriptor.topic}' has short_id '{short_id}' that ends with underscore (not allowed)")
    
    # Check for inappropriate metric types based on units
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

    # Check for inconsistent metric nature for energy metrics
    for descriptor in topics:
        if descriptor.metric_type == MetricType.ENERGY and descriptor.metric_nature != MetricNature.CUMULATIVE:
            errors.append(f"Topic '{descriptor.topic}' has metric_type ENERGY but metric_nature is {descriptor.metric_nature} (should be CUMULATIVE)")
        
        # Check for power metrics that should be instantaneous
        if descriptor.metric_type == MetricType.POWER and descriptor.metric_nature not in [MetricNature.INSTANTANEOUS, MetricNature.NONE]:
            errors.append(f"Topic '{descriptor.topic}' has metric_type POWER but metric_nature is {descriptor.metric_nature} (should be INSTANTANEOUS)")
       
    # Check for topics with min/max values but inappropriate message types
    for descriptor in topics:
        if (descriptor.min is not None or descriptor.max is not None) and descriptor.message_type not in [MetricKind.NUMBER]:
            errors.append(f"Topic '{descriptor.topic}' has min/max values but message_type is {descriptor.message_type} (should be NUMBER)")
    
    # Check for valid topic pattern structure
    for descriptor in topics:
        topic = descriptor.topic
        topic_parts = topic.split('/')
        if len(topic_parts) < 4:
            errors.append(f"Topic '{topic}' has invalid structure (too few parts)")
        if not topic.startswith('N/+/'):
            errors.append(f"Topic '{topic}' should start with 'N/+/'")
        
        # Check that all topics have between 2 and 3 plus signs
        plus_count = topic.count('+')
        if plus_count < 2:
            errors.append(f"Topic '{topic}' has only {plus_count} plus signs (minimum 2 required)")
        elif plus_count > 3:
            errors.append(f"Topic '{topic}' has {plus_count} plus signs (maximum 3 allowed)")
    
    # Check that topics with 3+ plus signs have {phase} in both short_id and name (except ATTRIBUTE types)
    for descriptor in topics:
        topic = descriptor.topic
        plus_count = topic.count('+')
        if plus_count == 3 and descriptor.message_type != MetricKind.ATTRIBUTE:
            # Check if short_id contains {phase}
            if descriptor.short_id and '{phase}' not in descriptor.short_id:
                errors.append(f"Topic '{topic}' has {plus_count} plus signs but short_id '{descriptor.short_id}' missing {{phase}} placeholder")
            
            # Check if name contains {phase}
            if descriptor.name and '{phase}' not in descriptor.name:
                errors.append(f"Topic '{topic}' has {plus_count} plus signs but name '{descriptor.name}' missing {{phase}} placeholder")
    
    # Check that no topic contains L1, L2, or L3 as literal parts
    for descriptor in topics:
        topic = descriptor.topic
        topic_parts = topic.split('/')
        for part in topic_parts:
            if part in ['L1', 'L2', 'L3']:
                errors.append(f"Topic '{topic}' contains literal phase identifier '{part}' - use '+' placeholder instead")
    
    # Check for invalid characters in topic strings
    for descriptor in topics:
        if '//' in descriptor.topic:
            errors.append(f"Topic '{descriptor.topic}' contains invalid '//' sequence")
    
    # Report all errors
    if errors:
        error_message = "\n".join([f"  - {error}" for error in errors])
        pytest.fail(f"Found {len(errors)} issues in topic_map:\n{error_message}")
    
    # If we reach here, all tests passed
    assert len(topics) > 0, "topics should not be empty"

def test_victron_enum_in_init():
    """Ensure all VictronEnum-derived enums are included in __init__.py's __all__."""
    from victron_mqtt.constants import VictronEnum
    from victron_mqtt import __all__

    # Collect all subclasses of VictronEnum
    victron_enum_classes = [cls.__name__ for cls in VictronEnum.__subclasses__()]

    # Check if all subclasses are in __all__
    missing_enums = [enum for enum in victron_enum_classes if enum not in __all__]

    assert not missing_enums, f"The following VictronEnum-derived enums are missing in __init__.py's __all__: {missing_enums}"

