"""Tests basic connectivity functionality. Does require a running Venus OS instance to connect to."""

import pytest
import victron_mqtt  # pylint: disable=import-error
import logging

# Configure logging
logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_connect(config_host, config_port, config_username, config_password, config_use_ssl, caplog):
    """Tests whether the client can connect to a Venus device. Disconnects after passing the test."""
    logger.debug("Starting test_connect")
    hub = victron_mqtt.Hub(config_host, config_port, config_username, config_password, config_use_ssl)
    await hub.connect()
    logger.debug("Connected to hub")
    assert hub.connected
    await hub.disconnect()
    logger.debug("Disconnected from hub")
    
    # Check that no error logs were emitted
    error_logs = [record for record in caplog.records if record.levelno >= logging.ERROR]
    assert len(error_logs) == 0, f"Test emitted {len(error_logs)} error log(s): {[record.message for record in error_logs]}"

@pytest.mark.asyncio
async def test_create_full_raw_snapshot(config_host, config_port, config_username, config_password, config_use_ssl, caplog):
    """
    Tests whether the client can connect to a Venus device and verify the connection details by
    checking whether a serial number could be obtained.
    """
    logger.debug("Starting test_create_full_raw_snapshot")
    hub = victron_mqtt.Hub(config_host, config_port, config_username, config_password, config_use_ssl)
    await hub.connect()
    logger.debug("Connected to hub")
    snapshot = await hub.create_full_raw_snapshot()
    logger.debug(f"Snapshot created with length: {len(snapshot)}")
    assert len(snapshot) > 0
    
    # Check that no error logs were emitted
    error_logs = [record for record in caplog.records if record.levelno >= logging.ERROR]
    assert len(error_logs) == 0, f"Test emitted {len(error_logs)} error log(s): {[record.message for record in error_logs]}"
