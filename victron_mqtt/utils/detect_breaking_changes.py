"""Detect breaking changes between two victron_mqtt.json snapshots.

Compares enum option IDs and topic short_ids between an old and new
``victron_mqtt.json`` file (produced by ``dump_victron_mqtt``).  Any removed
enum options or topic short_ids are reported as breaking changes.

Usage:
    python -m victron_mqtt.utils.detect_breaking_changes old.json new.json

Exit code: 0 = no breaking changes, 1 = breaking changes detected.
Output (stdout): Markdown-formatted breaking changes section, or empty.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .. import _victron_enums
from .._victron_topics import topics
from ..constants import VictronEnum


def load_surface(path: Path) -> dict[str, Any]:
    """Load a victron_mqtt.json and extract the API surface.

    Returns a dict with:
      - short_ids: {short_id: topic_path}
      - enum_ids:  {EnumName: {option_id: display_name}}
    """
    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    short_ids: dict[str, str] = {}
    topic_enums: dict[str, str] = {}
    for topic in data.get("topics", []):
        sid = topic.get("short_id", "")
        short_ids[sid] = topic.get("topic", "")
        enum_name = topic.get("enum")
        if enum_name:
            topic_enums[sid] = enum_name

    enum_ids: dict[str, dict[str, str]] = {}
    enum_values: dict[str, dict[str, int]] = {}
    for enum_def in data.get("enums", []):
        name = enum_def.get("name", "")
        enum_ids[name] = {ev.get("id", ""): ev.get("name", "") for ev in enum_def.get("EnumValues", [])}
        enum_values[name] = {ev.get("id", ""): ev.get("value", 0) for ev in enum_def.get("EnumValues", [])}

    return {"short_ids": short_ids, "enum_ids": enum_ids, "enum_values": enum_values, "topic_enums": topic_enums}


def load_surface_from_current() -> dict[str, Any]:
    """Build the API surface directly from the live Python objects.

    This avoids needing a pre-generated JSON file for the *new* side of the
    comparison.
    """

    short_ids: dict[str, str] = {t.short_id: t.topic for t in topics}

    topic_enums: dict[str, str] = {}
    for t in topics:
        if t.enum is not None:
            topic_enums[t.short_id] = type(t.enum).__name__

    enum_ids: dict[str, dict[str, str]] = {}
    enum_values: dict[str, dict[str, int]] = {}
    for name in dir(_victron_enums):
        obj = getattr(_victron_enums, name)
        if isinstance(obj, type) and issubclass(obj, VictronEnum) and obj is not VictronEnum:
            enum_ids[name] = {m.id: m.string for m in obj}
            enum_values[name] = {m.id: m.value for m in obj}

    return {"short_ids": short_ids, "enum_ids": enum_ids, "enum_values": enum_values, "topic_enums": topic_enums}


def compare_surfaces(old: dict[str, Any], new: dict[str, Any]) -> list[str]:
    """Compare two API surfaces and return breaking change descriptions."""
    changes: list[str] = []

    # Removed entities (short_id gone)
    old_sids = set(old["short_ids"])
    new_sids = set(new["short_ids"])
    changes.extend(
        f"- Entity `{sid}` was removed (topic: `{old['short_ids'][sid]}`)" for sid in sorted(old_sids - new_sids)
    )

    # Removed enum options
    for enum_name in sorted(set(old["enum_ids"]) & set(new["enum_ids"])):
        old_ids = set(old["enum_ids"][enum_name])
        new_ids = set(new["enum_ids"][enum_name])
        for eid in sorted(old_ids - new_ids):
            display = old["enum_ids"][enum_name][eid]
            changes.append(f'- `{enum_name}` option `{eid}` ("{display}") was removed')

    # Entirely removed enum classes
    changes.extend(
        f"- Enum `{enum_name}` was entirely removed"
        for enum_name in sorted(set(old["enum_ids"]) - set(new["enum_ids"]))
    )

    # Changed enum type on a topic — only breaking if value mappings differ
    old_te = old.get("topic_enums", {})
    new_te = new.get("topic_enums", {})
    old_ev = old.get("enum_values", {})
    new_ev = new.get("enum_values", {})
    for sid in sorted(set(old_te) & set(new_te)):
        if old_te[sid] != new_te[sid]:
            old_mapping = old_ev.get(old_te[sid], {})
            new_mapping = new_ev.get(new_te[sid], {})
            if old_mapping != new_mapping:
                # Build a human-readable description of the value changes
                old_ids = old.get("enum_ids", {}).get(old_te[sid], {})
                new_ids = new.get("enum_ids", {}).get(new_te[sid], {})
                old_desc = ", ".join(
                    f"{v}={old_ids.get(eid, eid)}" for eid, v in sorted(old_mapping.items(), key=lambda x: x[1])
                )
                new_desc = ", ".join(
                    f"{v}={new_ids.get(eid, eid)}" for eid, v in sorted(new_mapping.items(), key=lambda x: x[1])
                )
                changes.append(
                    f"- Entity `{sid}` changed enum from `{old_te[sid]}` to `{new_te[sid]}` "
                    f"— values are remapped ({old_desc} → {new_desc}). "
                    f"Check automations using this entity."
                )

    return changes


def format_breaking_changes(changes: list[str]) -> str:
    """Format breaking changes as a Markdown section."""
    if not changes:
        return ""
    lines = [
        "## ⚠️ Breaking Changes",
        "",
        "The following changes may break existing automations. Please review and update your automations accordingly.",
        "",
        *changes,
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Detect breaking changes between two victron_mqtt.json files.")
    parser.add_argument("old_json", type=Path, help="Previous version JSON")
    parser.add_argument(
        "new_json",
        type=Path,
        nargs="?",
        default=None,
        help="Current version JSON (omit to use live Python objects)",
    )
    args = parser.parse_args()

    old = load_surface(args.old_json)
    new = load_surface(args.new_json) if args.new_json is not None else load_surface_from_current()

    changes = compare_surfaces(old, new)
    output = format_breaking_changes(changes)

    if output:
        print(output)
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
