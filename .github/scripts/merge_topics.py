from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

# Entity types to include in the output. Add more as platforms are added.
# To publish all entity types, replace this with: INCLUDED_ENTITY_TYPES = None
INCLUDED_ENTITY_TYPES: set[str] | None = {"sensor", "select"}


def build_common_lookup(data: dict[str, Any], prefix: str = "") -> dict[str, list[str]]:
    """Build reverse lookup: value -> list of key paths from strings_common.json."""
    lookup: dict[str, list[str]] = {}
    for key, value in data.items():
        path = f"{prefix}::{key}" if prefix else key
        if isinstance(value, dict):
            for v, paths in build_common_lookup(cast("dict[str, Any]", value), path).items():
                lookup.setdefault(v, []).extend(paths)
        elif isinstance(value, str):
            lookup.setdefault(value, []).append(path)
    return lookup


def resolve_common_ref(value: str, common_lookup: dict[str, list[str]], prefer_section: str | None = None) -> str:
    """Replace a value with a [%key:...%] reference if found in common strings."""
    if value not in common_lookup:
        return value
    paths = common_lookup[value]
    if prefer_section:
        for path in paths:
            if prefer_section in path:
                return f"[%key:{path}%]"
    return f"[%key:{paths[0]}%]"


def main():
    parser = argparse.ArgumentParser(description="Merge victron_mqtt topics into strings.json")
    parser.add_argument("--topics", help="Path to victron_mqtt.json")
    parser.add_argument("--strings", help="Path to strings.json")
    parser.add_argument("--common", help="Path to strings_common.json")
    args = parser.parse_args()

    if args.topics and args.strings:
        topics_path = Path(args.topics)
        output_path = Path(args.strings)
    else:
        base = Path(__file__).parent.parent.parent
        topics_path = base / "victron_mqtt.json"
        translations_dir = base / "custom_components" / "victron_mqtt" / "translations"
        output_path = translations_dir / "strings.json"

    common_path = Path(args.common) if args.common else Path(__file__).parent / "strings_common.json"
    common_lookup: dict[str, list[str]] = {}
    if common_path.exists():
        with common_path.open(encoding="utf-8") as f:
            common_lookup = build_common_lookup(json.load(f))
        print(f"Loaded {len(common_lookup)} common string values from {common_path}")
    else:
        print(f"Warning: strings_common.json not found at {common_path}, skipping common references")

    print(f"topics_path={topics_path}")
    print(f"output_path={output_path}")
    with topics_path.open(encoding="utf-8") as f:
        topics_data = json.load(f)

    with output_path.open(encoding="utf-8") as f:
        en = json.load(f)

    # Build enum lookup: enum_name -> {lowercase_id: human_readable_name}
    enum_lookup: dict[str | None, dict[str, str]] = {}
    for enum_def in topics_data.get("enums", []):
        enum_name = enum_def.get("name")
        enum_values: dict[str, str] = {}
        for ev in enum_def.get("EnumValues", []):
            # Use lowercase id as key, name as value
            enum_values[ev.get("id", "").lower()] = ev.get("name", "")
        enum_lookup[enum_name] = enum_values

    # MetricTypes that map to a SensorDeviceClass in entity.py.
    # These get native_unit_of_measurement set in code, so the translation
    # file must NOT carry unit_of_measurement for them.
    DEVICE_CLASS_METRIC_TYPES = {
        "MetricType.POWER",
        "MetricType.APPARENT_POWER",
        "MetricType.ENERGY",
        "MetricType.VOLTAGE",
        "MetricType.CURRENT",
        "MetricType.FREQUENCY",
        "MetricType.ELECTRIC_STORAGE_PERCENTAGE",
        "MetricType.TEMPERATURE",
        "MetricType.SPEED",
        "MetricType.LIQUID_VOLUME",
        "MetricType.DURATION",
    }

    # Update topics: add or update entries in en.json under entity.sensor for each topic id
    entity: dict[str, dict[str, dict[str, Any]]] = {}
    count = 0
    for topic in topics_data.get("topics", []):
        translation_key = topic.get("short_id").replace("{", "").replace("}", "")  # same as in common.py
        topic_name = topic.get("generic_name")
        topic_unit = topic.get("unit_of_measurement")
        topic_metric_type = topic.get("metric_type")
        message_type = topic.get("message_type")
        is_adjustable_suffix = topic.get("is_adjustable_suffix")
        enum_name = topic.get("enum")
        is_main_topic = topic.get("main_topic", False)

        # Extract the part after the dot and make it lower case
        entity_type = message_type.split(".", 1)[1].lower() if "." in message_type else message_type.lower()

        if entity_type == "service":
            continue

        # Build entity entry with name and optional state for enums.
        # Only include unit_of_measurement in the translation when the metric
        # does NOT have a device_class (those get native_unit in code instead).
        # Main topics inherit their name from the device, so omit "name".
        entity_entry = {} if is_main_topic else {"name": topic_name}
        has_device_class = topic_metric_type in DEVICE_CLASS_METRIC_TYPES
        if topic_unit is not None and topic_unit != "%" and not has_device_class:
            entity_entry["unit_of_measurement"] = topic_unit
        if enum_name and enum_name in enum_lookup:
            entity_entry["state"] = {
                k: resolve_common_ref(v, common_lookup, prefer_section="common::state")
                for k, v in enum_lookup[enum_name].items()
            }

        # Add to original entity type
        if entity_type not in entity:
            entity[entity_type] = {}
        entity[entity_type][translation_key] = entity_entry
        count += 1

        # If is_adjustable_suffix is set, also add to sensor entity type
        if is_adjustable_suffix is not None and entity_type != "sensor":
            if "sensor" not in entity:
                entity["sensor"] = {}
            entity["sensor"][translation_key] = entity_entry
    # Sort the entity dictionary and its nested dictionaries
    sorted_entity: dict[str, dict[str, dict[str, Any]]] = {}
    for entity_type in sorted(entity.keys()):
        if INCLUDED_ENTITY_TYPES is not None and entity_type not in INCLUDED_ENTITY_TYPES:
            continue
        sorted_entity[entity_type] = {}
        for translation_key in sorted(entity[entity_type].keys()):
            entry = entity[entity_type][translation_key]
            sorted_entry = {}
            if "name" in entry:
                sorted_entry["name"] = entry["name"]
            if "unit_of_measurement" in entry and entity_type != "time":
                sorted_entry["unit_of_measurement"] = entry["unit_of_measurement"]
            if "state" in entry and entity_type != "button":
                # For binary_sensor and switches, skip state if it only has on/off options
                state_keys = set(entry["state"].keys())
                if entity_type in ["binary_sensor", "switch"] and state_keys <= {"on", "off"}:
                    pass
                else:
                    # Sort the state dictionary alphabetically by key
                    sorted_entry["state"] = dict(sorted(entry["state"].items()))
            if sorted_entry:
                sorted_entity[entity_type][translation_key] = sorted_entry

    en["entity"] = sorted_entity

    # Build lookup of units from generated English entity translations
    units_lookup: dict[str, dict[str, Any]] = {}
    for entity_type, entries in sorted_entity.items():
        units_lookup[entity_type] = {}
        for translation_key, entry in entries.items():
            if "unit_of_measurement" in entry:
                units_lookup[entity_type][translation_key] = entry["unit_of_measurement"]

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(en, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")

    print(f"Updated {count} entities")


if __name__ == "__main__":
    main()
