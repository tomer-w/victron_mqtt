"""
Support for Victron Venus WritableMetric.
"""

from __future__ import annotations

import asyncio
import logging

from typing import TYPE_CHECKING, Callable, NamedTuple

from victron_mqtt.constants import FormulaPersistentState, FormulaTransientState

if TYPE_CHECKING:
    from .device import Device

from .metric import Metric
from .data_classes import TopicDescriptor
from . import _victron_formulas as formulas

_LOGGER = logging.getLogger(__name__)


class FormulaMetric(Metric):
    """Representation of a Victron Venus sensor."""

    def __init__(self, device: Device, unique_id: str, name: str, descriptor: TopicDescriptor) -> None:
        """Initialize the FormulaMetric."""
        _LOGGER.debug(
            "Creating new FormulaMetric: unique_id=%s, type=%s, nature=%s",
            unique_id, descriptor.metric_type, descriptor.metric_nature
        )
        assert descriptor.is_formula, f"Metric {unique_id} is not a formula"
        self._depends_on: dict[str, Metric] = {}
        self.transient_state: FormulaTransientState | None = None
        self.persistent_state: FormulaPersistentState | None = None
        super().__init__(device, unique_id, name, descriptor, descriptor.short_id, {})

    def phase2_init(self, depends_on: dict[str, Metric], event_loop: asyncio.AbstractEventLoop | None, log_debug: Callable[..., None]) -> None:
        self._depends_on = depends_on
        self._handle_formula(event_loop, log_debug)

    def __repr__(self) -> str:
        return f"FormulaMetric({super().__repr__()}, transient_state={self.transient_state}, persistent_state={self.persistent_state})"
    
    @property
    def value(self):
        return self._value

    def _handle_formula(self, event_loop: asyncio.AbstractEventLoop | None, log_debug: Callable[..., None]):
        func_name = self._descriptor.topic.split('/')[-1]
        func = getattr(formulas, func_name)
        value, self.transient_state, self.persistent_state = func(self._depends_on, self.transient_state, self.persistent_state)
        if value is not None:
            self._handle_message(value, event_loop, log_debug)
