
from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from .device import Device

class LastReading(NamedTuple):
    timestamp: datetime
    value: float
    accumulated_energy: float

def get_system_battery_power(installation_id: str, devices: dict[str, Device]) -> float | None:
    system_device_name = f"{installation_id}_system_0"
    system_device = devices.get(system_device_name)
    if system_device:
        system_dc_battery_power_metric_name = f"{system_device_name}_system_dc_battery_power"
        system_dc_battery_power_metric = system_device.get_metric_from_unique_id(system_dc_battery_power_metric_name)
        if system_dc_battery_power_metric and system_dc_battery_power_metric.value:
            return system_dc_battery_power_metric.value
    return None

def calculate_rolling_riemann_sum(
    current_power: float, 
    current_time: datetime,
    last_reading: LastReading | None,
    time_interval: float
) -> LastReading:
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
        return LastReading(current_time, current_power, 0.0)
        
    # Calculate time difference
    dt = (current_time - last_reading.timestamp).total_seconds()
    # Use the minimum of actual time difference and requested interval
    dt = min(dt, time_interval)
    
    # Left Riemann sum uses the left (previous) value
    interval_energy = last_reading.value * dt if last_reading.value > 0 else 0.0
    
    # Create new last reading with updated accumulated energy
    new_last_reading = LastReading(
        timestamp=current_time,
        value=current_power,
        accumulated_energy=last_reading.accumulated_energy + interval_energy
    )
    
    return new_last_reading

def system_dc_battery_charge_power(
    installation_id: str, 
    devices: dict[str, Device],
    last_reading: LastReading | None,
    time_interval: float) -> tuple[float, LastReading | None]:
    """
    Calculate current power and accumulated energy using rolling Left Riemann Sum.
    
    Args:
        installation_id: The installation ID
        devices: Dictionary of available devices
        last_reading: Previous reading with accumulated energy
        time_interval: Time interval in seconds for the Riemann sum calculation
        
    Returns:
        Tuple of (accumulated_energy, new_last_reading):
        - accumulated_energy: Total energy accumulated since first reading
        - new_last_reading: Updated last reading with accumulated energy
    """
    current_power = get_system_battery_power(installation_id, devices)
    
    # If we don't have a current power reading, we can't calculate energy
    if current_power is None:
        return last_reading.accumulated_energy if last_reading else 0.0, last_reading
    
    if current_power < 0:
        current_power = 0.0  # Only consider charging power for energy accumulation

    # Calculate rolling Riemann sum
    current_time = datetime.now()
    new_last_reading = calculate_rolling_riemann_sum(
        current_power=current_power,
        current_time=current_time,
        last_reading=last_reading,
        time_interval=time_interval
    )
    
    return new_last_reading.accumulated_energy, new_last_reading
