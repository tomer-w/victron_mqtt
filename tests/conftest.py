"""Configuration for tests, mostly Victron Venus device connection settings.

Can be overridden by environment variables:
VENUS_TEST_HOST - The host or IP address of the Venus device. Default "venus.local."
VENUS_TEST_PORT - The port of the Venus device. Default 1883
VENUS_TEST_USERNAME - The username for the Venus device. Default None
VENUS_TEST_PASSWORD - The password for the Venus device. Default None
VENUS_TEST_USE_SSL - Whether to use SSL for the connection. Default False

"""

import os
import pytest
import traceback
import asyncio

orig_close = asyncio.BaseEventLoop.close

def debug_close(self):
    print("Event loop is being closed. Call stack:")
    #traceback.print_stack()
    orig_close(self)

asyncio.BaseEventLoop.close = debug_close

@pytest.fixture
def config_host():
    return os.getenv("VICTRON_MQTT_SERVER", "venus.local.")


@pytest.fixture
def config_port():
    return int(os.getenv("VICTRON_MQTT_PORT", "1883"))


@pytest.fixture
def config_username():
    return os.getenv("VICTRON_TEST_USERNAME", None)


@pytest.fixture
def config_password():
    return os.getenv("VICTRON_TEST_PASSWORD", None)

@pytest.fixture
def config_root_prefix():
    return os.getenv("VICTRON_TEST_ROOT_PREFIX", None)

@pytest.fixture
def config_use_ssl() -> bool:
    use_ssl_str = os.getenv("VENUS_TEST_USE_SSL", "False")
    return use_ssl_str.lower() in ["true", "1", "t", "y", "yes", "on"]
