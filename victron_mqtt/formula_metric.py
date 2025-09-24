"""
Support for Victron Venus WritableMetric.
"""

from __future__ import annotations

import asyncio
import logging

from typing import TYPE_CHECKING, Callable

from victron_mqtt.constants import FormulaPersistentState, FormulaTransientState

if TYPE_CHECKING:
    from .hub import Hub
    from .device import Device

from .metric import Metric
from .data_classes import TopicDescriptor
from . import _victron_formulas as formulas

_LOGGER = logging.getLogger(__name__)


class FormulaMetric(Metric):
    """Representation of a Victron Venus sensor."""

    def __init__(self, device: Device, unique_id: str, name: str, descriptor: TopicDescriptor, hub: Hub) -> None:
        """Initialize the FormulaMetric."""
        _LOGGER.debug(
            "Creating new FormulaMetric: unique_id=%s, type=%s, nature=%s",
            unique_id, descriptor.metric_type, descriptor.metric_nature
        )
        assert descriptor.is_formula, f"Metric {unique_id} is not a formula"
        self._depends_on: dict[str, Metric] = {}
        self.transient_state: FormulaTransientState | None = None
        self.persistent_state: FormulaPersistentState | None = None
        super().__init__(device, unique_id, name, descriptor, descriptor.short_id, {}, hub)

    def init(self, depends_on: dict[str, Metric], event_loop: asyncio.AbstractEventLoop | None, log_debug: Callable[..., None]) -> None:
        self._depends_on = depends_on
        self._handle_formula(event_loop, log_debug)

    def __str__(self) -> str:
        return f"FormulaMetric({super().__str__()}, transient_state={self.transient_state}, persistent_state={self.persistent_state})"

    def __repr__(self) -> str:
        return self.__str__()
    
    @property
    def value(self):
        return self._value

    def _handle_formula(self, event_loop: asyncio.AbstractEventLoop | None, log_debug: Callable[..., None]):
        func_name = self._descriptor.topic.split('/')[-1]
        func = getattr(formulas, func_name)
        # Formula functions may return None to indicate no value/update.
        result = func(self._depends_on, self.transient_state, self.persistent_state)
        if result is None:
            log_debug("Formula %s returned None", func_name)
            self._handle_message(None, event_loop, log_debug)
            return
        
        try:
            value, self.transient_state, self.persistent_state = result
        except Exception:  # pragma: no cover - defensive logging for unexpected return shapes
            _LOGGER.error("Unexpected return value from formula %s: %r", func_name, result)
            return
        
        if self._descriptor.precision is not None:
            value = round(value, self._descriptor.precision)
        self._handle_message(value, event_loop, log_debug)
