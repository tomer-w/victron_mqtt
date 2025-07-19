"""Tests that devices and metrics can be enumerated."""

import pytest
import victron_mqtt
import logging


@pytest.mark.asyncio
async def test_devices_and_metrics(config_host, config_port, config_username, config_password, config_use_ssl, caplog, config_root_prefix):
    hub = victron_mqtt.Hub(config_host, config_port, config_username, config_password, config_use_ssl, topic_prefix=config_root_prefix)
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
    
    # Check that no error logs were emitted
    error_logs = [record for record in caplog.records if record.levelno >= logging.ERROR]
    assert len(error_logs) == 0, f"Test emitted {len(error_logs)} error log(s): {[record.message for record in error_logs]}"
