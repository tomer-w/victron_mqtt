"""Tests for the product capability lookup feature.

Covers the VictronProductId enum, the product capability registry, and the
resolution of ProductCapabilityRef range values on writable metrics.
"""

import pytest

from victron_mqtt._victron_enums import VictronProductId
from victron_mqtt._victron_products import (
    ProductCapabilities,
    get_product_capabilities,
)
from victron_mqtt._victron_topics import topics
from victron_mqtt.constants import MetricKind, MetricType, RangeType
from victron_mqtt.data_classes import ProductCapabilityRef, TopicDescriptor
from victron_mqtt.writable_metric import WritableMetric


class _StubDevice:
    """Minimal stand-in exposing just the product_id property used by resolution."""

    def __init__(self, product_id: int | None) -> None:
        self.product_id = product_id


def _make_writable_with_ref(ref: ProductCapabilityRef, product_id: int | None) -> WritableMetric:
    metric = WritableMetric.__new__(WritableMetric)
    metric._key_values = {}
    metric._descriptor = TopicDescriptor(
        topic="mock",
        message_type=MetricKind.NUMBER,
        short_id="mock",
        name="mock",
        metric_type=MetricType.CURRENT,
        max=ref,
    )
    metric._device = _StubDevice(product_id)  # type: ignore[assignment]
    return metric


# ---------------------------------------------------------------------------
# VictronProductId enum
# ---------------------------------------------------------------------------


class TestVictronProductId:
    def test_from_code_hex(self):
        assert VictronProductId.from_code(0xA057) is VictronProductId.SMARTSOLAR_MPPT_100_50

    def test_unique_codes(self):
        codes = [member.code for member in VictronProductId]
        assert len(codes) == len(set(codes)), "Duplicate product ID codes"

    def test_unique_ids(self):
        ids = [member.id for member in VictronProductId]
        assert len(ids) == len(set(ids)), "Duplicate product ID ids"

    def test_unknown_code(self):
        assert VictronProductId.from_code(0xFFFF) is None

    def test_readable_string(self):
        assert VictronProductId.SMARTSOLAR_MPPT_100_50.string == "SmartSolar MPPT 100/50"


# ---------------------------------------------------------------------------
# get_product_capabilities
# ---------------------------------------------------------------------------


class TestGetProductCapabilities:
    def test_known_by_int(self):
        caps = get_product_capabilities(0xA057)
        assert caps is not None
        assert caps.max_charge_current == 50

    def test_known_other_model(self):
        caps = get_product_capabilities(0xA063)
        assert caps is not None
        assert caps.max_charge_current == 70

    def test_unknown_returns_none(self):
        assert get_product_capabilities(0xFFFF) is None

    def test_none_returns_none(self):
        assert get_product_capabilities(None) is None

    def test_every_table_entry_has_positive_current(self):
        for member in VictronProductId:
            caps = get_product_capabilities(member.code)
            if caps is not None and caps.max_charge_current is not None:
                assert caps.max_charge_current > 0


# ---------------------------------------------------------------------------
# ProductCapabilityRef resolution on writable metrics
# ---------------------------------------------------------------------------


class TestResolveProductCapability:
    def test_resolves_known_product(self):
        ref = ProductCapabilityRef("max_charge_current", 200)
        metric = _make_writable_with_ref(ref, product_id=0xA057)
        assert metric._resolve_range_value(ref, "device_0", {}) == 50

    def test_falls_back_to_default_for_unknown_product(self):
        ref = ProductCapabilityRef("max_charge_current", 200)
        metric = _make_writable_with_ref(ref, product_id=0xFFFF)
        assert metric._resolve_range_value(ref, "device_0", {}) == 200

    def test_falls_back_to_default_when_no_product_id(self):
        ref = ProductCapabilityRef("max_charge_current", 200)
        metric = _make_writable_with_ref(ref, product_id=None)
        assert metric._resolve_range_value(ref, "device_0", {}) == 200

    def test_falls_back_to_default_for_unknown_capability(self):
        ref = ProductCapabilityRef("does_not_exist", 123)
        metric = _make_writable_with_ref(ref, product_id=0xA057)
        assert metric._resolve_range_value(ref, "device_0", {}) == 123

    def test_static_numeric_still_resolves(self):
        ref = ProductCapabilityRef("max_charge_current", 200)
        metric = _make_writable_with_ref(ref, product_id=0xA057)
        assert metric._resolve_range_value(0, "device_0", {}) == 0
        assert metric._resolve_range_value(None, "device_0", {}) is None


# ---------------------------------------------------------------------------
# Topic wiring
# ---------------------------------------------------------------------------


class TestChargeCurrentTopicsWiring:
    @pytest.mark.parametrize(
        "short_id",
        ["solarcharger_charge_current_limit", "alternator_charge_current_limit"],
    )
    def test_charge_current_limit_uses_product_capability_ref(self, short_id):
        descriptor = next(t for t in topics if t.short_id == short_id)
        assert isinstance(descriptor.max, ProductCapabilityRef)
        assert descriptor.max.capability == "max_charge_current"
        assert descriptor.max.default == 200
        # DYNAMIC so a GX-reported max still takes precedence over the table.
        assert descriptor.min_max_range == RangeType.DYNAMIC

    def test_default_matches_capabilities_dataclass_field(self):
        # Guard against typos: the referenced capability must exist on the dataclass.
        descriptor = next(t for t in topics if t.short_id == "solarcharger_charge_current_limit")
        assert isinstance(descriptor.max, ProductCapabilityRef)
        assert hasattr(ProductCapabilities(), descriptor.max.capability)
