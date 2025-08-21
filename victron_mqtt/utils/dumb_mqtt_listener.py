import argparse
import paho.mqtt.client as mqtt
from victron_mqtt._victron_topics import topics

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker successfully.")
        if userdata['only_supported_victron']:
            for topic in userdata['victron_topics']:
                client.subscribe(topic)
                print(f"Subscribed to: {topic}")
        else:
            client.subscribe("#")  # Subscribe to all topics
            print("Subscribed to all topics.")
    else:
        print(f"Failed to connect, return code {rc}")

def on_message(client, userdata, msg):
    print(f"{msg.topic}: {msg.payload.decode()}")

def main():
    parser = argparse.ArgumentParser(description="MQTT Listener CLI")
    parser.add_argument("--host", required=True, help="MQTT broker host")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--only_supported_victron", action="store_true", help="Subscribe only to supported Victron topics")
    args = parser.parse_args()

    victron_topics = [descriptor.topic for descriptor in topics]

    client = mqtt.Client(userdata={
        'only_supported_victron': args.only_supported_victron,
        'victron_topics': victron_topics
    })
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