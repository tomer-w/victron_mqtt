import json
from datetime import datetime

import pytest

from victron_mqtt._unwrappers import (
    unwrap_bool,
    unwrap_int,
    unwrap_int_default_0,
    unwrap_int_seconds_to_hours,
    unwrap_float,
    unwrap_string,
    unwrap_enum,
    unwrap_epoch,
    wrap_enum,
    wrap_int,
    wrap_int_default_0,
    wrap_int_hours_to_seconds,
    wrap_float,
    wrap_string,
    wrap_epoch,
    VALUE_TYPE_UNWRAPPER,
    VALUE_TYPE_WRAPPER,
)
from victron_mqtt._victron_enums import GenericOnOff
from victron_mqtt.constants import ValueType


def test_unwrap_bool_true_false_null_and_malformed():
    assert unwrap_bool('{"value": true}') is True
    assert unwrap_bool('{"value": false}') is False
    assert unwrap_bool('{"value": 1}') is True
    assert unwrap_bool('{"value": 0}') is False
    assert unwrap_bool('{"value": null}') is None
    assert unwrap_bool('not json') is None


def test_unwrap_int_and_default():
    assert unwrap_int('{"value": 5}') == 5
    assert unwrap_int('{"value": "7"}') == 7
    assert unwrap_int('{"value": null}') is None
    assert unwrap_int('bad') is None

    assert unwrap_int_default_0('{"value": 3}') == 3
    assert unwrap_int_default_0('{"value": null}') == 0
    assert unwrap_int_default_0('bad') == 0


def test_unwrap_float_variants():
    # existing zero tests
    assert unwrap_float('{"value": 0}', None) == 0.0
    assert unwrap_float('{"value": 0}', 2) == 0.0
    assert unwrap_float('{"value": "0"}', 3) == 0.0

    # json_value parameter
    json_str = '{"value": 2.3456, "other": 1.2344}'
    assert unwrap_float(json_str, 2, json_value="other") == 1.23

    # None value
    assert unwrap_float('{"value": null}', None) is None
    # malformed
    assert unwrap_float('not json', None) is None


def test_unwrap_string():
    assert unwrap_string('{"value": "abc"}') == "abc"
    assert unwrap_string('{"value": 1}') == "1"
    assert unwrap_string('{"value": null}') is None
    assert unwrap_string('bad') is None


def test_unwrap_enum_and_epoch():
    # GenericOnOff: Off=0, On=1
    res = unwrap_enum('{"value": 1}', GenericOnOff)
    assert res is GenericOnOff.On
    assert unwrap_enum('{"value": null}', GenericOnOff) is None
    assert unwrap_enum('bad', GenericOnOff) is None

    # epoch
    ts = 1609459200  # 2021-01-01 00:00:00 UTC
    dt = datetime.fromtimestamp(ts)
    res_dt = unwrap_epoch(json.dumps({"value": ts}))
    assert isinstance(res_dt, datetime)
    assert res_dt == dt


def test_unwrap_int_seconds_to_hours():
    # Test normal conversion: 3600 seconds = 1 hour
    assert unwrap_int_seconds_to_hours('{"value": 3600}', None) == 1.0
    assert unwrap_int_seconds_to_hours('{"value": 7200}', None) == 2.0
    
    # Test with precision
    assert unwrap_int_seconds_to_hours('{"value": 1800}', 2) == 0.5  # 30 minutes
    assert unwrap_int_seconds_to_hours('{"value": 900}', 3) == 0.25  # 15 minutes
    
    # Test rounding with precision
    assert unwrap_int_seconds_to_hours('{"value": 3661}', 2) == 1.02  # 1 hour 1 minute 1 second
    
    # Test null value
    assert unwrap_int_seconds_to_hours('{"value": null}', None) is None
    assert unwrap_int_seconds_to_hours('{"value": null}', 2) is None
    
    # Test malformed JSON
    assert unwrap_int_seconds_to_hours('bad json', None) is None
    assert unwrap_int_seconds_to_hours('bad json', 2) is None
    
    # Test zero seconds
    assert unwrap_int_seconds_to_hours('{"value": 0}', None) == 0.0


def test_wrap_int_hours_to_seconds():
    # Test normal conversion: 1 hour = 3600 seconds
    assert json.loads(wrap_int_hours_to_seconds(1)) == {"value": 3600}
    assert json.loads(wrap_int_hours_to_seconds(2)) == {"value": 7200}
    
    # Test fractional hours (though function expects int, test edge case)
    assert json.loads(wrap_int_hours_to_seconds(0)) == {"value": 0}
    
    # Test None value
    assert json.loads(wrap_int_hours_to_seconds(None)) == {"value": None}


def test_wrap_functions_and_mappings():
    # wrap_int
    assert json.loads(wrap_int(5)) == {"value": 5}
    assert json.loads(wrap_int(None)) == {"value": None}

    # wrap_int_default_0
    assert json.loads(wrap_int_default_0(7)) == {"value": 7}
    assert json.loads(wrap_int_default_0(None)) == {"value": 0}

    # wrap_float and wrap_string
    assert json.loads(wrap_float(1.23)) == {"value": 1.23}
    assert json.loads(wrap_string("abc")) == {"value": "abc"}

    # wrap_enum with enum instance
    assert json.loads(wrap_enum(GenericOnOff.On, GenericOnOff)) == {"value": GenericOnOff.On.code}
    # wrap_enum with string name
    assert json.loads(wrap_enum("On", GenericOnOff)) == {"value": GenericOnOff.On.code}

    # wrap_epoch
    dt = datetime(2020, 1, 2, 3, 4, 5)
    out = json.loads(wrap_epoch(dt))
    assert "value" in out
    # epoch should be close to datetime.timestamp
    assert abs(out["value"] - datetime.timestamp(dt)) < 1e-6

    # mappings contain expected types
    assert ValueType.FLOAT in VALUE_TYPE_UNWRAPPER
    assert ValueType.FLOAT in VALUE_TYPE_WRAPPER
    assert ValueType.INT_SECONDS_TO_HOURS in VALUE_TYPE_UNWRAPPER
    assert ValueType.INT_SECONDS_TO_HOURS in VALUE_TYPE_WRAPPER
    assert callable(VALUE_TYPE_UNWRAPPER[ValueType.FLOAT])
    assert callable(VALUE_TYPE_WRAPPER[ValueType.FLOAT])
    assert callable(VALUE_TYPE_UNWRAPPER[ValueType.INT_SECONDS_TO_HOURS])
    assert callable(VALUE_TYPE_WRAPPER[ValueType.INT_SECONDS_TO_HOURS])
