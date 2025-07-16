"""Functions to unwrap the data from the JSON string."""

from enum import Enum
import json

from victron_mqtt.constants import ValueType, VictronEnum


def unwrap_int(json_str):
    """Unwrap an integer value from a JSON string."""
    try:
        data = json.loads(json_str)
        if data["value"] is None:
            return None
        return int(data["value"])
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        return None


def unwrap_int_default_0(json_str):
    """Unwrap an integer value from a JSON string, defaulting to 0."""
    try:
        data = json.loads(json_str)
        if data["value"] is None:
            return 0
        return int(data["value"])
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        return 0


def unwrap_float(json_str):
    """Unwrap a float value from a JSON string."""
    try:
        data = json.loads(json_str)
        if data["value"] is None:
            return None
        return float(data["value"])
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        return None


def unwrap_string(json_str):
    """Unwrap a string value from a JSON string."""
    try:
        data = json.loads(json_str)
        if data["value"] is None:
            return None
        return str(data["value"])
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        return None


def unwrap_enum(json_str, enum: type[VictronEnum]):
    """Unwrap a string value from a JSON string."""
    try:
        data = json.loads(json_str)
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        return None
    val = data["value"]
    return enum.from_code(val) if val is not None else None


def wrap_enum(enum_val: Enum | str, enum_expected: type[VictronEnum]) -> str:
    """Wrap an Enum value into a JSON string with a 'value' key."""
    if isinstance(enum_val, VictronEnum):
        return json.dumps({"value": enum_val.code})
    elif isinstance(enum_val, str):
        return json.dumps({"value": enum_expected.from_string(enum_val).code})
    else:
        raise TypeError(f"Expected Enum or str, got {type(enum_val).__name__}")


def wrap_int(value: int | None) -> str:
    """Wrap an integer value into a JSON string with a 'value' key."""
    return json.dumps({"value": value})


def wrap_int_default_0(value: int | None) -> str:
    """Wrap an integer value into a JSON string with a 'value' key, defaulting to 0 if None."""
    return json.dumps({"value": value if value is not None else 0})


def wrap_float(value: float | None) -> str:
    """Wrap a float value into a JSON string with a 'value' key."""
    return json.dumps({"value": value})


def wrap_string(value: str | None) -> str:
    """Wrap a string value into a JSON string with a 'value' key."""
    return json.dumps({"value": value})


VALUE_TYPE_UNWRAPPER = {
    ValueType.INT: unwrap_int,
    ValueType.INT_DEFAULT_0: unwrap_int_default_0,
    ValueType.FLOAT: unwrap_float,
    ValueType.STRING: unwrap_string,
    ValueType.ENUM: unwrap_enum,
}

VALUE_TYPE_WRAPPER = {
    ValueType.INT: wrap_int,
    ValueType.INT_DEFAULT_0: wrap_int_default_0,
    ValueType.FLOAT: wrap_float,
    ValueType.STRING: wrap_string,
    ValueType.ENUM: wrap_enum,
}
