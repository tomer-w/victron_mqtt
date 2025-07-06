"""
Command-line tool to dump all data from topic_map and enums in _victron_enums.py to JSON.
"""


import json
import argparse

from .._victron_topics import topic_map, MetricKind
from .. import _victron_enums
from ..constants import VictronEnum

def enum_to_dict(enum_cls):
    # Handles both Enum and IntEnum, flattening tuple values if present
    result = {"name": enum_cls.__name__, "EnumValues": []}
    for k, v in enum_cls.__members__.items():
        val = v.value
        result["EnumValues"].append({
            "id": k,
            "name": val[1],
            "value": val[0],
        })
    return result

def get_all_enums(module):
    enums = []
    for name in dir(module):
        obj = getattr(module, name)
        if (
            isinstance(obj, type)
            and issubclass(obj, VictronEnum)
            and obj is not VictronEnum
        ):
            enums.append(enum_to_dict(obj))
    return enums


def main():
    parser = argparse.ArgumentParser(description="Dump topic_map and enums to JSON.")
    parser.add_argument("output_file", help="Output JSON file name")
    args = parser.parse_args()

    def topic_dict_with_enum_name(k, v):
        d = {"topic": k, **v.__dict__}
        if "enum" in d and d["enum"] is not None:
            d["enum"] = d["enum"].__name__
        return d

    data = {
        "topics": [
            topic_dict_with_enum_name(k, v)
            for k, v in topic_map.items()
            if getattr(v, "message_type", None) != MetricKind.ATTRIBUTE
        ],
        "enums": get_all_enums(_victron_enums),
    }
    with open(args.output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)

if __name__ == "__main__":
    main()
