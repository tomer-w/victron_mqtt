
from __future__ import annotations
from typing import TYPE_CHECKING

from .writable_metric import WritableMetric
from ._victron_enums import ChargeSchedule, GenericOnOff
from .formula_common import left_riemann_sum_internal
from .constants import FormulaPersistentState, FormulaTransientState

if TYPE_CHECKING:
    from .metric import Metric

def system_dc_battery_discharge_power(
    depends_on: dict[str, Metric],
    transient_state: FormulaTransientState | None,
    persistent_state: FormulaPersistentState | None) -> tuple[float, FormulaTransientState, FormulaPersistentState] | None:
    
    def adjust_power_for_discharging(current_power: float) -> float:
        if current_power > 0:
            current_power = 0.0
        else:
            current_power = current_power * -1 / 1000
        return current_power

    return left_riemann_sum_internal(depends_on, adjust_power_for_discharging, transient_state, persistent_state)

def system_dc_battery_charge_power(
    depends_on: dict[str, Metric],
    transient_state: FormulaTransientState | None,
    persistent_state: FormulaPersistentState | None) -> tuple[float, FormulaTransientState, FormulaPersistentState] | None:

    def adjust_power_for_charging(current_power: float) -> float:
        if current_power < 0:
            current_power = 0.0  # Only consider charging power for energy accumulation
        return current_power / 1000

    return left_riemann_sum_internal(depends_on, adjust_power_for_charging, transient_state, persistent_state)

def left_riemann_sum(
    depends_on: dict[str, Metric],
    transient_state: FormulaTransientState | None,
    persistent_state: FormulaPersistentState | None) -> tuple[float, FormulaTransientState, FormulaPersistentState] | None:   

    def adjust(input: float) -> float:
        return input / 1000  # Convert to kW
    
    return left_riemann_sum_internal(depends_on, adjust, transient_state, persistent_state)


def schedule_charge_enabled(
    depends_on: dict[str, Metric],
    transient_state: FormulaTransientState | None,
    persistent_state: FormulaPersistentState | None) -> tuple[GenericOnOff | None, None, None]:   

    assert len(depends_on) == 1, "Expected exactly one input metric for schedule_charge_enabled"
    metric = list(depends_on.values())[0]
    if metric.value is None:
        return None, None, None
    
    ret_val = GenericOnOff.On if metric.value.code >= 0 else GenericOnOff.Off
    return ret_val, None, None

def schedule_charge_enabled_set(
    value: str,
    depends_on: dict[str, Metric],
    transient_state: FormulaTransientState | None,
    persistent_state: FormulaPersistentState | None) -> tuple[GenericOnOff, None, None]:   
    assert len(depends_on) == 1, "Expected exactly one input metric for schedule_charge_enabled"
    enabled: GenericOnOff | None = value if isinstance(value, GenericOnOff) else GenericOnOff.from_string(value) #Support both the int value and the enum itself
    assert enabled is not None, "Failed to determine enabled state"
    metric = list(depends_on.values())[0]
    assert isinstance(metric, WritableMetric), "Expected WritableMetric for schedule_charge_enabled_set"
    assert isinstance(metric.value, ChargeSchedule), "Expected ChargeSchedule for schedule_charge_enabled_set.value"
    schedule_value = metric.value
    if enabled == GenericOnOff.On:
        if schedule_value == ChargeSchedule.DisabledSunday:
            metric.set(ChargeSchedule.Sunday) # No idea why they didnt choose non zero for Sunday
        elif schedule_value.code < 0:
            metric.set(ChargeSchedule.from_code(abs(schedule_value.code))) # type: ignore
    else:
        if schedule_value == ChargeSchedule.Sunday:
            metric.set(ChargeSchedule.DisabledSunday) # No idea why they didnt choose non zero for Sunday
        elif schedule_value.code >= 0:
            metric.set(ChargeSchedule.from_code(-abs(schedule_value.code))) # type: ignore

    return enabled, None, None