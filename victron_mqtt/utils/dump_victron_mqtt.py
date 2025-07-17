
"""
Command-line tool to dump all data from topics list and enums in _victron_enums.py to JSON.
"""


import json
import argparse

from .._victron_topics import topics
from ..constants import MetricKind
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
    parser = argparse.ArgumentParser(description="Dump topics and enums to JSON.")
    parser.add_argument("output_file", help="Output JSON file name")
    args = parser.parse_args()

    def topic_dict_with_enum_name(descriptor):
        d = {"topic": descriptor.topic, **descriptor.__dict__}
        if "enum" in d and d["enum"] is not None:
            d["enum"] = d["enum"].__name__
        return d

    # Metadata block similar to canboat.json
    metadata = {
        "SchemaVersion": "1.0.0",
        "Comment": "See https://github.com/tomer-w/victron_mqtt for the full source code",
        "CreatorCode": "dump_victron_mqtt.py",
        "License": "Apache License Version 2.0",
        "Version": "1.0.0",
        "Copyright": "victron_mqtt (C) 2025, Tomer-w (https://github.com/tomer-w).\nFor more information see https://github.com/tomer-w/victron_mqtt\n\nThis file is part of victron_mqtt.\n\nLicensed under the Apache License, Version 2.0 (the 'License'); you may not use this file except in compliance with the License. You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0\n\nUnless required by applicable law or agreed to in writing, software distributed under the License is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License."
    }

    data = {
        **metadata,
        "topics": [
            topic_dict_with_enum_name(descriptor)
            for descriptor in topics
            if getattr(descriptor, "message_type", None) != MetricKind.ATTRIBUTE
        ],
        "enums": get_all_enums(_victron_enums),
    }
    with open(args.output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)

if __name__ == "__main__":
    main()
