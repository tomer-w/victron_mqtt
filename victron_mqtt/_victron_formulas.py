
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from .constants import FormulaPersistentState, FormulaTransientState

if TYPE_CHECKING:
    from .metric import Metric

@dataclass
class LRSLastReading(FormulaTransientState):
    timestamp: datetime
    value: float | None
    accumulated_energy: float

@dataclass
class LRSPersistentState(FormulaPersistentState):
    accumulated_energy: float | None

def get_system_battery_power(depends_on: dict[str, Metric]) -> float:
    system_dc_battery_power_metric = list(depends_on.values())[0]
    assert system_dc_battery_power_metric is not None, "Missing system DC battery power metric"
    assert system_dc_battery_power_metric.value is not None, "System DC battery power metric has no value"
    return system_dc_battery_power_metric.value

def calculate_rolling_riemann_sum(
    current_power: float, 
    current_time: datetime,
    last_reading: LRSLastReading | None,
    time_interval: float
) -> LRSLastReading:
    """
    Calculate the Left Riemann Sum using only the last reading.
    
    Args:
        current_power: Current power reading
        current_time: Current timestamp
        last_reading: Previous reading with its accumulated energy
        time_interval: Maximum time interval to consider
        
    Returns:
        new_last_reading: Updated last reading with accumulated energy
    """
    # Only consider positive power for charging
    current_power = max(0, current_power)
    
    if last_reading is None:
        # First reading, no energy accumulated yet
        return LRSLastReading(current_time, current_power, 0.0)
        
    # Calculate time difference
    dt = (current_time - last_reading.timestamp).total_seconds()
    # Use the minimum of actual time difference and requested interval
    dt = min(dt, time_interval)
    
    # Left Riemann sum uses the left (previous) value
    interval_energy = last_reading.value * dt if last_reading.value is not None and last_reading.value > 0 else 0.0
    
    # Create new last reading with updated accumulated energy
    new_last_reading = LRSLastReading(
        timestamp=current_time,
        value=current_power,
        accumulated_energy=last_reading.accumulated_energy + interval_energy
    )
    
    return new_last_reading

def system_dc_battery_discharge_power(
    depends_on: dict[str, Metric],
    transient_state: FormulaTransientState | None,
    persistent_state: FormulaPersistentState | None) -> tuple[float, FormulaTransientState, FormulaPersistentState]:
    
    current_power = get_system_battery_power(depends_on)
    if current_power > 0:
        current_power = 0.0
    else:
        current_power = current_power * -1
    return system_dc_battery_charge_power_internal(current_power, transient_state, persistent_state)

def system_dc_battery_charge_power(
    depends_on: dict[str, Metric],
    transient_state: FormulaTransientState | None,
    persistent_state: FormulaPersistentState | None) -> tuple[float, FormulaTransientState, FormulaPersistentState]:

    current_power = get_system_battery_power(depends_on)
    if current_power < 0:
        current_power = 0.0  # Only consider charging power for energy accumulation
    return system_dc_battery_charge_power_internal(current_power, transient_state, persistent_state)

def system_dc_battery_charge_power_internal(
    current_power: float,
    transient_state: FormulaTransientState | None,
    persistent_state: FormulaPersistentState | None,) -> tuple[float, FormulaTransientState, FormulaPersistentState]:
    """
    Calculate current power and accumulated energy using rolling Left Riemann Sum.
    
    Args:
        depends_on: Dictionary of metrics to depend on
        last_reading: Previous reading with accumulated energy
        time_interval: Time interval in seconds for the Riemann sum calculation
        
    Returns:
        Tuple of (accumulated_energy, new_last_reading):
        - accumulated_energy: Total energy accumulated since first reading
        - new_last_reading: Updated last reading with accumulated energy
    """ 
    assert transient_state is None or isinstance(transient_state, LRSLastReading)
    if not persistent_state:
        persistent_state = LRSPersistentState(accumulated_energy=0.0)

    assert isinstance(persistent_state, LRSPersistentState)
    
    # Calculate rolling Riemann sum
    current_time = datetime.now()
    new_last_reading = calculate_rolling_riemann_sum(
        current_power=current_power,
        current_time=current_time,
        last_reading=transient_state,
        time_interval=30
    )
    persistent_state.accumulated_energy = new_last_reading.accumulated_energy
    return new_last_reading.accumulated_energy, new_last_reading, persistent_state
