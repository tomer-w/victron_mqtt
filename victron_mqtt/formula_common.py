from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Callable

from .constants import FormulaPersistentState, FormulaTransientState

if TYPE_CHECKING:
    from .metric import Metric

@dataclass
class LRSLastReading(FormulaTransientState):
    timestamp: datetime
    value: float | None
    accumulated_value: float

@dataclass
class LRSPersistentState(FormulaPersistentState):
    accumulated_value: float | None

def get_lrs_input(depends_on: dict[str, Metric]) -> float | None:
    assert len(depends_on) == 1, "Expected exactly one input metric for LRS"
    metric = list(depends_on.values())[0]
    return metric.value

def calculate_rolling_riemann_sum(
    current_reading: float, 
    current_time: datetime,
    last_reading: LRSLastReading | None,
    time_interval: float
) -> LRSLastReading:
    """
    Calculate the Left Riemann Sum using only the last reading.

    Args:
        current_power: Current power reading
        current_time: Current timestamp
        last_reading: Previous reading with its accumulated value
        time_interval: Maximum time interval to consider

    Returns:
        new_last_reading: Updated last reading with accumulated result in hours
    """
    # Only consider positive readings
    current_power = max(0, current_reading)
    
    if last_reading is None:
        # First reading, no energy accumulated yet
        return LRSLastReading(current_time, current_reading, 0.0)
        
    # Calculate time difference
    dt = (current_time - last_reading.timestamp).total_seconds()
    assert dt >= 0, f"Negative time difference: {dt}"
    # Use the minimum of actual time difference and requested interval (both in seconds)
    dt = min(dt, time_interval)

    # Convert dt from seconds to hours for Wh (W * hours = Wh)
    dt_hours = dt / 3600.0

    # Left Riemann sum uses the left (previous) value. Only positive previous
    # power contributes to accumulated charging energy.
    interval_energy = (
        last_reading.value * dt_hours
        if last_reading.value is not None and last_reading.value > 0
        else 0.0
    )
    
    # Create new last reading with updated accumulated energy
    new_last_reading = LRSLastReading(
        timestamp=current_time,
        value=current_power,
        accumulated_value=last_reading.accumulated_value + interval_energy
    )
    
    return new_last_reading

def left_riemann_sum_internal(
    depends_on: dict[str, Metric],
    adjust_reading: Callable[[float], float],
    transient_state: FormulaTransientState | None,
    persistent_state: FormulaPersistentState | None,) -> tuple[float, FormulaTransientState, FormulaPersistentState] | None:
    """
    Calculate rolling Left Riemann Sum on input.
    
    Args:
        depends_on: Dictionary of metrics to depend on
        last_reading: Previous reading with accumulated value
        time_interval: Time interval in seconds for the Riemann sum calculation
        
    Returns:
        Tuple of (accumulated_energy, new_last_reading):
        - accumulated_energy: Total energy accumulated since first reading
        - new_last_reading: Updated last reading with accumulated result
    """ 
    current_reading = get_lrs_input(depends_on)
    if current_reading is None:
        return None
    current_reading = adjust_reading(current_reading)

    assert transient_state is None or isinstance(transient_state, LRSLastReading)
    if not persistent_state:
        persistent_state = LRSPersistentState(accumulated_value=0.0)

    assert isinstance(persistent_state, LRSPersistentState)
    
    # Calculate rolling Riemann sum
    current_time = datetime.now()
    new_last_reading = calculate_rolling_riemann_sum(
        current_reading=current_reading,
        current_time=current_time,
        last_reading=transient_state,
        time_interval=30
    )
    persistent_state.accumulated_value = new_last_reading.accumulated_value
    return new_last_reading.accumulated_value, new_last_reading, persistent_state
