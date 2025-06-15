# SPDX-FileCopyrightText: 2024-present Johan du Plessis https://github.com/johanslab
#
# SPDX-License-Identifier: MIT
"""Tests basic connectivity functionality. Does require a running Venus OS instance to connect to."""

import pytest
import victron_mqtt  # pylint: disable=import-error


@pytest.mark.asyncio
async def test_connect(config_host, config_port, config_username, config_password, config_use_ssl):
    """Tests whether the client can connect to a Venus device. Disconnects after passing the test."""
    hub = victron_mqtt.Hub(config_host, config_port, config_username, config_password, config_use_ssl)
    await hub.connect()
    assert hub.connected
    await hub.disconnect()


@pytest.mark.asyncio
async def test_verify_connection(config_host, config_port, config_username, config_password, config_use_ssl):
    """
    Tests whether the client can connect to a Venus device and verify the connection details by
    checking whether a serial number could be obtained.
    """
    hub = victron_mqtt.Hub(config_host, config_port, config_username, config_password, config_use_ssl)
    serial = await hub.verify_connection_details()
    assert len(serial) > 0
