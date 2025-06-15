from asyncio import run
from victron_mqtt import Hub, Device, Metric


async def main():
    hub = Hub("venus.local.", 1883, None, None, False)
    await hub.connect()
    print("Connected!")

    await hub.initialize_devices_and_metrics()
    print("Got all the devices and metrics!")

    devices = hub.devices
    for device in devices:
        print(f"Device: {device.model}")
        metrics = device.metrics
        for metric in metrics:
            print(f"   {metric.short_id}{metric.formatted_value}")

    await hub.disconnect()


if __name__ == "__main__":
    run(main())
