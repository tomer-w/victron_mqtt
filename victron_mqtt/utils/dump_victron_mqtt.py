"""Command-line tool to dump topics and enums to JSON."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypedDict

from .. import _victron_enums
from .._victron_topics import topics
from ..constants import MetricKind, VictronEnum

if TYPE_CHECKING:
    from types import ModuleType

    from ..data_classes import TopicDescriptor


class EnumValueDump(TypedDict):
    """Serialized representation of a single enum value."""

    id: str
    name: str
    value: int | str


class EnumDump(TypedDict):
    """Serialized representation of a Victron enum."""

    name: str
    EnumValues: list[EnumValueDump]


METADATA: dict[str, str] = {
    "SchemaVersion": "1.0.0",
    "Comment": "See https://github.com/tomer-w/victron_mqtt for the full source code",
    "CreatorCode": "dump_victron_mqtt.py",
    "License": "Apache License Version 2.0",
    "Version": "1.0.0",
    "Copyright": "victron_mqtt (C) 2026, Tomer-w (https://github.com/tomer-w).\n"
    "For more information see https://github.com/tomer-w/victron_mqtt\n\n"
    "This file is part of victron_mqtt.\n\n"
    "Licensed under the Apache License, Version 2.0 (the 'License'); you may not "
    "use this file except in compliance with the License. You may obtain a copy "
    "of the License at http://www.apache.org/licenses/LICENSE-2.0\n\n"
    "Unless required by applicable law or agreed to in writing, software "
    "distributed under the License is distributed on an 'AS IS' BASIS, WITHOUT "
    "WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the "
    "License for the specific language governing permissions and limitations "
    "under the License.",
}


def enum_to_dict(enum_cls: type[VictronEnum]) -> EnumDump:
    """Convert a Victron enum class to a serializable dictionary."""
    enum_values: list[EnumValueDump] = [
        {
            "id": member.id,
            "name": member.string,
            "value": member.code,
        }
        for member in enum_cls
    ]
    return {
        "name": enum_cls.__name__,
        "EnumValues": enum_values,
    }


def get_all_enums(module: ModuleType) -> list[EnumDump]:
    """Collect all VictronEnum-derived classes from a module."""
    enums: list[EnumDump] = []
    for name in dir(module):
        obj: object = getattr(module, name)
        if (
            isinstance(obj, type)
            and issubclass(obj, VictronEnum)
            and obj is not VictronEnum
        ):
            enums.append(enum_to_dict(obj))
    return enums


def topic_dict_with_enum_name(descriptor: TopicDescriptor) -> dict[str, Any]:
    """Convert a TopicDescriptor to dict and replace enum class with its class name."""
    topic_data: dict[str, Any] = {
        "topic": descriptor.topic,
        **asdict(descriptor),
    }
    enum_cls = topic_data.get("enum")
    if isinstance(enum_cls, type) and issubclass(enum_cls, VictronEnum):
        topic_data["enum"] = enum_cls.__name__
    return topic_data


def main() -> None:
    """Run the dump utility as a command-line tool."""
    parser = argparse.ArgumentParser(description="Dump topics and enums to JSON.")
    parser.add_argument("output_file", type=Path, help="Output JSON file name")
    args = parser.parse_args()

    data: dict[str, Any] = {
        **METADATA,
        "topics": [
            topic_dict_with_enum_name(descriptor)
            for descriptor in topics
            if descriptor.message_type != MetricKind.ATTRIBUTE
        ],
        "enums": get_all_enums(_victron_enums),
    }

    with args.output_file.open("w", encoding="utf-8") as output_file:
        json.dump(data, output_file, indent=2, default=str)


if __name__ == "__main__":
    main()
