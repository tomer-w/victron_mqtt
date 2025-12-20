"""
Support for Victron Venus WritableMetric.
"""

from __future__ import annotations

import logging

from typing import Callable

from .constants import FormulaPersistentState, FormulaTransientState
from .metric import Metric
from .data_classes import TopicDescriptor
from . import _victron_formulas as formulas

_LOGGER = logging.getLogger(__name__)


class FormulaMetric(Metric):
    """Representation of a Victron Venus sensor."""

    def __init__(self, *, descriptor: TopicDescriptor, **kwargs) -> None:
        """Initialize the FormulaMetric."""
        _LOGGER.debug(
            "Creating new FormulaMetric: unique_id=%s, type=%s, nature=%s",
            descriptor.short_id, descriptor.metric_type, descriptor.metric_nature
        )
        assert descriptor.is_formula, f"Metric {descriptor.short_id} is not a formula"
        self._depends_on: dict[str, Metric] = {}
        self.transient_state: FormulaTransientState | None = None
        self.persistent_state: FormulaPersistentState | None = None
        assert descriptor.topic.startswith("$$func")
        func_name = descriptor.topic.split('/')[-1]
        if ":" in func_name:
            func_name = func_name.split(":", 1)[0]
        self._func = getattr(formulas, func_name)

        super().__init__(descriptor = descriptor, **kwargs)

    def init(self, depends_on: dict[str, Metric], log_debug: Callable[..., None]) -> None:
        self._depends_on = depends_on
        self._handle_formula(log_debug)

    def __str__(self) -> str:
        return f"FormulaMetric({super().__str__()}, transient_state={self.transient_state}, persistent_state={self.persistent_state})"

    def __repr__(self) -> str:
        return self.__str__()
    
    @property
    def value(self):
        return self._value

    def _handle_formula(self, log_debug: Callable[..., None]):
        # Formula functions may return None to indicate no value/update.
        result = self._func(self._depends_on, self.transient_state, self.persistent_state)
        if result is None:
            log_debug("Formula %s returned None", self._func)
            self._handle_message(None, log_debug)
            return
        
        try:
            value, self.transient_state, self.persistent_state = result
        except Exception:  # pragma: no cover - defensive logging for unexpected return shapes
            _LOGGER.error("Unexpected return value from formula %s: %r", self._func, result)
            return
        
        if self._descriptor.precision is not None:
            value = round(value, self._descriptor.precision)
        self._handle_message(value, log_debug)
