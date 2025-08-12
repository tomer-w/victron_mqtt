"""Tests basic connectivity functionality. Does require a running Venus OS instance to connect to."""

import pytest
import victron_mqtt  # pylint: disable=import-error
import logging

from victron_mqtt._victron_enums import DeviceType

# Configure logging
logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_connect(config_host, config_port, config_username, config_password, config_use_ssl, caplog, config_root_prefix):
    """Tests whether the client can connect to a Venus device. Disconnects after passing the test."""
    logger.debug("Starting test_connect")
    hub = victron_mqtt.Hub(config_host, config_port, config_username, config_password, config_use_ssl, topic_prefix=config_root_prefix)
    await hub.connect()
    logger.debug("Connected to hub")
    assert hub.connected
    await hub.disconnect()
    logger.debug("Disconnected from hub")
    
    # Check that no error logs were emitted
    error_logs = [record for record in caplog.records if record.levelno >= logging.ERROR]
    assert len(error_logs) == 0, f"Test emitted {len(error_logs)} error log(s): {[record.message for record in error_logs]}"

@pytest.mark.asyncio
async def test_create_full_raw_snapshot(config_host, config_port, config_username, config_password, config_use_ssl, caplog, config_root_prefix):
    """
    Tests whether the client can connect to a Venus device and verify the connection details by
    checking whether a serial number could be obtained.
    """
    logger.debug("Starting test_create_full_raw_snapshot")
    hub = victron_mqtt.Hub(config_host, config_port, config_username, config_password, config_use_ssl, topic_prefix=config_root_prefix)
    await hub.connect()
    logger.debug("Connected to hub")
    snapshot = await hub.create_full_raw_snapshot()
    logger.debug(f"Snapshot created with length: {len(snapshot)}")
    assert len(snapshot) > 0
    
    # Check that no error logs were emitted
    error_logs = [record for record in caplog.records if record.levelno >= logging.ERROR]
    assert len(error_logs) == 0, f"Test emitted {len(error_logs)} error log(s): {[record.message for record in error_logs]}"

@pytest.mark.asyncio
async def test_devices_and_metrics(config_host, config_port, config_username, config_password, config_use_ssl, caplog, config_root_prefix):
    hub = victron_mqtt.Hub(config_host, config_port, config_username, config_password, config_use_ssl, topic_prefix=config_root_prefix)
    await hub.connect()

    assert len(hub.devices) > 0

    for device in hub.devices:
        assert device.device_type is not None
        if device.device_type == DeviceType.UNKNOWN or device.device_type == DeviceType.GENERATOR:
            continue
        assert len(device.metrics) > 0

        for metric in device.metrics:
            assert metric.short_id is not None
            assert len(metric.short_id) > 0

    await hub.disconnect()
    
    # Check that no error logs were emitted
    error_logs = [record for record in caplog.records if record.levelno >= logging.ERROR]
    assert len(error_logs) == 0, f"Test emitted {len(error_logs)} error log(s): {[record.message for record in error_logs]}"


@pytest.mark.asyncio
async def test_two_hubs_connect(config_host, config_port, config_username, config_password, config_use_ssl, caplog, config_root_prefix):
    """Tests whether the client can connect to two Venus devices. Disconnects after passing the test."""
    logger.debug("Starting test_two_hubs_connect")
    hub1 = victron_mqtt.Hub(config_host, config_port, config_username, config_password, config_use_ssl, topic_prefix=config_root_prefix)
    hub2 = victron_mqtt.Hub(config_host, config_port, config_username, config_password, config_use_ssl, topic_prefix=config_root_prefix)
    await hub1.connect()
    assert hub1.connected
    await hub2.connect()
    assert hub2.connected
    logger.debug("Connected to both hubs")
    await hub1.disconnect()
    await hub2.disconnect()
    logger.debug("Disconnected from both hubs")

    # Check that no error logs were emitted
    error_logs = [record for record in caplog.records if record.levelno >= logging.ERROR]
    assert len(error_logs) == 0, f"Test emitted {len(error_logs)} error log(s): {[record.message for record in error_logs]}"
