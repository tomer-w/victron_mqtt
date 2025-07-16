"""Tests that devices and metrics can be enumerated."""

import pytest
import victron_mqtt


@pytest.mark.asyncio
async def test_devices_and_metrics(config_host, config_port, config_username, config_password, config_use_ssl):
    hub = victron_mqtt.Hub(config_host, config_port, config_username, config_password, config_use_ssl)
    await hub.connect()

    assert len(hub.devices) > 0

    for device in hub.devices:
        assert device.device_type is not None
        if device.device_type == victron_mqtt.DeviceType.UNKNOWN:
            continue
        assert len(device.metrics) > 0

        for metric in device.metrics:
            assert metric.short_id is not None
            assert len(metric.short_id) > 0

    await hub.disconnect()
