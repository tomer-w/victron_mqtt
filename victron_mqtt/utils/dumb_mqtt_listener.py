"""Minimal MQTT listener CLI for printing raw Victron broker traffic."""

import argparse
from typing import Any

import paho.mqtt.client as mqtt

from .._victron_topics import topics
from ..constants import TOPIC_INSTALLATION_ID

KEEPALIVE_PAYLOAD = '{ "keepalive-options" : [{"full-publish-completed-echo": "dumb-mqtt-listener"}]}'


def on_connect(client: mqtt.Client, userdata: dict[str, Any], _flags: dict[str, int], rc: int) -> None:
    """Subscribe to topics once connected to the broker."""
    if rc == 0:
        print("Connected to MQTT broker successfully.")
        userdata["seeded_installation_ids"].clear()
        if userdata["only_supported_victron"]:
            for topic in userdata["victron_topics"]:
                client.subscribe(topic)
                print(f"Subscribed to: {topic}")
        else:
            client.subscribe("#")  # Subscribe to all topics
            print("Subscribed to all topics.")
        if userdata["seed_victron"]:
            client.subscribe(TOPIC_INSTALLATION_ID)
            print(f"Subscribed to installation discovery topic: {TOPIC_INSTALLATION_ID}")
    else:
        print(f"Failed to connect, return code {rc}")


def on_message(client: mqtt.Client, userdata: dict[str, Any], msg: mqtt.MQTTMessage) -> None:
    """Print each received MQTT message."""
    print(f"{msg.topic}: {msg.payload.decode()}")
    topic_parts = msg.topic.split("/")
    if (
        userdata["seed_victron"]
        and len(topic_parts) == 5
        and topic_parts[0] == "N"
        and topic_parts[2:] == ["system", "0", "Serial"]
        and topic_parts[1] not in userdata["seeded_installation_ids"]
    ):
        installation_id = topic_parts[1]
        keepalive_topic = f"R/{installation_id}/keepalive"
        client.publish(keepalive_topic, KEEPALIVE_PAYLOAD)
        userdata["seeded_installation_ids"].add(installation_id)
        print(f"Seeded Victron installation {installation_id} via: {keepalive_topic}")


def main() -> None:
    """Parse CLI arguments and run the MQTT listener loop."""
    parser = argparse.ArgumentParser(description="MQTT Listener CLI")
    parser.add_argument("--host", required=True, help="MQTT broker host")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument(
        "--only_supported_victron", action="store_true", help="Subscribe only to supported Victron topics"
    )
    parser.add_argument(
        "--seed_victron",
        action="store_true",
        help="Request a full publish after discovering each Victron installation",
    )
    args = parser.parse_args()

    victron_topics = [descriptor.topic for descriptor in topics]

    client = mqtt.Client(
        userdata={
            "only_supported_victron": args.only_supported_victron,
            "victron_topics": victron_topics,
            "seed_victron": args.seed_victron,
            "seeded_installation_ids": set(),
        }
    )
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        print(f"Connecting to MQTT broker at {args.host}:{args.port}...")
        client.connect(args.host, args.port, 60)
        client.loop_forever()
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
