
from __future__ import annotations
from typing import TYPE_CHECKING

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
            current_power = current_power * -1
        return current_power

    return left_riemann_sum_internal(depends_on, adjust_power_for_discharging, transient_state, persistent_state)

def system_dc_battery_charge_power(
    depends_on: dict[str, Metric],
    transient_state: FormulaTransientState | None,
    persistent_state: FormulaPersistentState | None) -> tuple[float, FormulaTransientState, FormulaPersistentState] | None:

    def adjust_power_for_charging(current_power: float) -> float:
        if current_power < 0:
            current_power = 0.0  # Only consider charging power for energy accumulation
        return current_power

    return left_riemann_sum_internal(depends_on, adjust_power_for_charging, transient_state, persistent_state)

def left_riemann_sum(
    depends_on: dict[str, Metric],
    transient_state: FormulaTransientState | None,
    persistent_state: FormulaPersistentState | None) -> tuple[float, FormulaTransientState, FormulaPersistentState] | None:   

    def adjust(input: float) -> float:
        return input
    
    return left_riemann_sum_internal(depends_on, adjust, transient_state, persistent_state)

