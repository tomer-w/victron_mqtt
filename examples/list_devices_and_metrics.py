import asyncio
import logging

import victron_mqtt


# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - [Thread %(thread)d] - %(message)s'
)


async def main():
    # Create a hub connection
    hub = victron_mqtt.Hub("venus.local.", 1883, None, None, False)

    # Connect and initialize
    await hub.connect()

    # Access devices and metrics
    for device in hub.devices:
        print(f"Device: {device.model} ({device.device_type})")
        for metric in device.metrics:
            print(f"  {metric.short_id}: {metric.formatted_value}")

    await hub.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
