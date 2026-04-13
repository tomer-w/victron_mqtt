"""Victron formula implementations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ._victron_enums import ChargeSchedule, GenericOnOff
from .data_classes import GpsLocation
from .formula_common import left_riemann_sum_internal
from .writable_metric import WritableMetric

if TYPE_CHECKING:
    from .constants import FormulaTransientState
    from .metric import Metric


def system_dc_battery_discharge_power(
    depends_on: dict[str, Metric], transient_state: FormulaTransientState | None
) -> tuple[float, FormulaTransientState] | None:
    """Calculate the system DC battery discharge power in kWh."""

    def adjust_power_for_discharging(current_power: float) -> float:
        return 0.0 if current_power > 0 else current_power * -1 / 1000

    return left_riemann_sum_internal(depends_on, adjust_power_for_discharging, transient_state)


def system_dc_battery_charge_power(
    depends_on: dict[str, Metric], transient_state: FormulaTransientState | None
) -> tuple[float, FormulaTransientState] | None:
    """Calculate the system DC battery charge power in kWh."""

    def adjust_power_for_charging(current_power: float) -> float:
        if current_power < 0:
            current_power = 0.0  # Only consider charging power for energy accumulation
        return current_power / 1000

    return left_riemann_sum_internal(depends_on, adjust_power_for_charging, transient_state)


def left_riemann_sum(
    depends_on: dict[str, Metric], transient_state: FormulaTransientState | None
) -> tuple[float, FormulaTransientState] | None:
    """Calculate the left Riemann sum in kWh."""

    def adjust(val: float) -> float:
        return val / 1000  # Convert to kW

    return left_riemann_sum_internal(depends_on, adjust, transient_state)


def schedule_charge_enabled(
    depends_on: dict[str, Metric], _transient_state: FormulaTransientState | None
) -> tuple[GenericOnOff | None, None]:
    """Determine if schedule charge is enabled."""

    assert len(depends_on) == 1, "Expected exactly one input metric for schedule_charge_enabled"
    metric = next(iter(depends_on.values()))
    if metric.value is None:
        return None, None

    ret_val = GenericOnOff.ON if metric.value.code >= 0 else GenericOnOff.OFF
    return ret_val, None


def schedule_charge_enabled_set(
    value: str, depends_on: dict[str, Metric], _transient_state: FormulaTransientState | None
) -> tuple[GenericOnOff, None]:
    """Set schedule charge enabled state."""

    assert len(depends_on) == 1, "Expected exactly one input metric for schedule_charge_enabled"
    enabled: GenericOnOff | None = (
        value if isinstance(value, GenericOnOff) else GenericOnOff.from_id_or_string(value)
    )  # Support both the int value and the enum itself
    assert enabled is not None, "Failed to determine enabled state"
    metric = next(iter(depends_on.values()))
    assert isinstance(metric, WritableMetric), "Expected WritableMetric for schedule_charge_enabled_set"
    assert isinstance(metric.value, ChargeSchedule), "Expected ChargeSchedule for schedule_charge_enabled_set.value"
    schedule_value = metric.value
    schedule_code = schedule_value.code
    assert isinstance(schedule_code, int), "Expected integer code for ChargeSchedule"
    if enabled == GenericOnOff.ON:
        if schedule_value == ChargeSchedule.DISABLED_SUNDAY:
            metric.set(ChargeSchedule.SUNDAY)  # No idea why they didnt choose non zero for Sunday
        elif schedule_code < 0:
            metric.set(ChargeSchedule.from_code(abs(schedule_code)))  # type: ignore[arg-type]
    elif schedule_value == ChargeSchedule.SUNDAY:
        metric.set(ChargeSchedule.DISABLED_SUNDAY)  # No idea why they didnt choose non zero for Sunday
    elif schedule_code >= 0:
        metric.set(ChargeSchedule.from_code(-abs(schedule_code)))  # type: ignore[arg-type]

    return enabled, None


def gps_location(
    depends_on: dict[str, Metric],
    _transient_state: FormulaTransientState | None,
) -> tuple[GpsLocation | None, None]:
    """Combine GPS metrics into a single GpsLocation. Returns None when there is no GPS fix."""
    lat_metric = None
    lon_metric = None
    fix_metric = None
    alt_metric = None
    course_metric = None
    speed_metric = None
    for metric in depends_on.values():
        if metric.generic_short_id == "gps_latitude":
            lat_metric = metric
        elif metric.generic_short_id == "gps_longitude":
            lon_metric = metric
        elif metric.generic_short_id == "gps_fix":
            fix_metric = metric
        elif metric.generic_short_id == "gps_altitude":
            alt_metric = metric
        elif metric.generic_short_id == "gps_course":
            course_metric = metric
        elif metric.generic_short_id == "gps_speed":
            speed_metric = metric

    if lat_metric is None or lon_metric is None:
        return None, None
    if lat_metric.value is None or lon_metric.value is None:
        return None, None

    # No fix means position is unreliable
    if fix_metric is not None and fix_metric.value == GenericOnOff.OFF:
        return None, None

    return GpsLocation(
        latitude=lat_metric.value,
        longitude=lon_metric.value,
        altitude=alt_metric.value if alt_metric else None,
        course=course_metric.value if course_metric else None,
        speed=speed_metric.value if speed_metric else None,
    ), None
