"""Tests for the GX firmware update lifecycle."""

import asyncio
import json
from typing import TYPE_CHECKING, cast

import pytest

from victron_mqtt import FirmwareUpdateError, FirmwareUpdateErrorReason, FirmwareUpdateState, Hub
from victron_mqtt.testing import create_mocked_hub, inject_message

if TYPE_CHECKING:
    from unittest.mock import MagicMock

INSTALL_TOPIC_SUFFIX = "/platform/0/Firmware/Online/Install"
CHECK_TOPIC_SUFFIX = "/platform/0/Firmware/Online/Check"


async def _inject_value(hub: Hub, topic: str, value: object) -> None:
    await inject_message(hub, topic, json.dumps({"value": value}))


async def _inject_firmware_info(
    hub: Hub,
    *,
    installed: str = "v3.60",
    available: str = "v3.70",
    state: int = 1000,
    progress: int | None = None,
) -> None:
    await _inject_value(hub, "N/123/platform/0/Firmware/Installed/Version", installed)
    await _inject_value(hub, "N/123/platform/0/Firmware/Online/AvailableVersion", available)
    await _inject_value(hub, "N/123/platform/0/Firmware/State", state)
    await _inject_value(hub, "N/123/platform/0/Firmware/Progress", progress)
    hub._handle_full_publish_message(skip_validation=True)


@pytest.mark.asyncio
async def test_firmware_update_info_normalizes_progress() -> None:
    hub = await create_mocked_hub(installation_id="123")
    await _inject_firmware_info(hub, state=1003, progress=42)

    info = hub.firmware_update_info

    assert info.installed_version == "v3.60"
    assert info.available_version == "v3.70"
    assert info.state is FirmwareUpdateState.REBOOTING
    assert info.progress == 100
    assert info.in_progress
    assert info.update_available


@pytest.mark.asyncio
async def test_check_firmware_update_publishes_periodically() -> None:
    hub = await create_mocked_hub(installation_id="123")
    hub.check_firmware_update(poll_interval=0.01)
    await asyncio.sleep(0.025)
    hub._stop_firmware_update_checks()

    publish = cast("MagicMock", hub._client.publish)
    checks = [
        call
        for call in publish.call_args_list
        if call.args[0].endswith(CHECK_TOPIC_SUFFIX) and call.args[1] == '{"value": 1}'
    ]
    assert len(checks) >= 2


@pytest.mark.asyncio
async def test_check_firmware_update_replaces_existing_schedule() -> None:
    hub = await create_mocked_hub(installation_id="123")
    hub.check_firmware_update(poll_interval=60)
    first_task = hub._firmware_check_task

    hub.check_firmware_update(poll_interval=60)
    await asyncio.sleep(0)

    assert first_task is not None
    assert first_task.cancelled()
    assert hub._firmware_check_task is not first_task
    hub._stop_firmware_update_checks()


@pytest.mark.asyncio
async def test_disconnect_stops_firmware_update_checks() -> None:
    hub = await create_mocked_hub(installation_id="123")
    hub.check_firmware_update()
    task = hub._firmware_check_task

    await hub.disconnect()

    assert task is not None
    assert task.cancelled()
    assert hub._firmware_check_task is None


@pytest.mark.asyncio
async def test_check_firmware_update_rejects_invalid_interval() -> None:
    hub = await create_mocked_hub(installation_id="123")

    with pytest.raises(ValueError, match="poll_interval must be greater than zero"):
        hub.check_firmware_update(0)


@pytest.mark.asyncio
async def test_check_firmware_update_publishes_immediately() -> None:
    hub = await create_mocked_hub(installation_id="123")
    hub.check_firmware_update()
    await asyncio.sleep(0)
    hub._stop_firmware_update_checks()

    publish = cast("MagicMock", hub._client.publish)
    assert any(
        call.args[0].endswith(CHECK_TOPIC_SUFFIX) and call.args[1] == '{"value": 1}' for call in publish.call_args_list
    )


@pytest.mark.asyncio
async def test_install_firmware_update_reports_progress_and_completes() -> None:
    hub = await create_mocked_hub(installation_id="123")
    await _inject_firmware_info(hub)
    progress: list[int] = []

    task = asyncio.create_task(hub.install_firmware_update(progress.append, poll_interval=0.001))
    await asyncio.sleep(0)
    await _inject_value(hub, "N/123/platform/0/Firmware/State", 1002)
    await _inject_value(hub, "N/123/platform/0/Firmware/Progress", -5)
    await asyncio.sleep(0.01)
    await _inject_value(hub, "N/123/platform/0/Firmware/Progress", 45)
    await asyncio.sleep(0.01)
    await _inject_value(hub, "N/123/platform/0/Firmware/Installed/Version", "v3.70")
    await task

    publish = cast("MagicMock", hub._client.publish)
    assert progress == [0, 45, 100]
    assert any(
        call.args[0].endswith(INSTALL_TOPIC_SUFFIX) and call.args[1] == '{"value": 1}'
        for call in publish.call_args_list
    )


@pytest.mark.asyncio
async def test_install_firmware_update_resumes_active_install() -> None:
    hub = await create_mocked_hub(installation_id="123")
    await _inject_firmware_info(hub, state=1002, progress=50)

    task = asyncio.create_task(hub.install_firmware_update(poll_interval=0.001))
    await asyncio.sleep(0.01)
    await _inject_value(hub, "N/123/platform/0/Firmware/Installed/Version", "v3.70")
    await task

    publish = cast("MagicMock", hub._client.publish)
    assert not any(call.args[0].endswith(INSTALL_TOPIC_SUFFIX) for call in publish.call_args_list)


@pytest.mark.asyncio
async def test_install_firmware_update_raises_device_error() -> None:
    hub = await create_mocked_hub(installation_id="123")
    await _inject_firmware_info(hub)

    task = asyncio.create_task(hub.install_firmware_update(poll_interval=0.001))
    await asyncio.sleep(0)
    await _inject_value(hub, "N/123/platform/0/Firmware/State", 998)

    with pytest.raises(FirmwareUpdateError) as raised:
        await task

    assert raised.value.reason is FirmwareUpdateErrorReason.ERROR_DURING_UPDATE


@pytest.mark.asyncio
async def test_install_firmware_update_times_out() -> None:
    hub = await create_mocked_hub(installation_id="123")
    await _inject_firmware_info(hub)

    with pytest.raises(FirmwareUpdateError) as raised:
        await hub.install_firmware_update(timeout=0.01, poll_interval=0.001)

    assert raised.value.reason is FirmwareUpdateErrorReason.UPDATE_TIMED_OUT


@pytest.mark.asyncio
async def test_install_firmware_update_ignores_stale_error() -> None:
    hub = await create_mocked_hub(installation_id="123")
    await _inject_firmware_info(hub, state=998)

    task = asyncio.create_task(hub.install_firmware_update(poll_interval=0.001))
    await asyncio.sleep(0.01)
    assert not task.done()

    await _inject_value(hub, "N/123/platform/0/Firmware/State", 1000)
    await _inject_value(hub, "N/123/platform/0/Firmware/State", 998)

    with pytest.raises(FirmwareUpdateError) as raised:
        await task

    assert raised.value.reason is FirmwareUpdateErrorReason.ERROR_DURING_UPDATE


@pytest.mark.asyncio
async def test_install_firmware_update_rejects_concurrent_monitor() -> None:
    hub = await create_mocked_hub(installation_id="123")
    await _inject_firmware_info(hub)
    first_task = asyncio.create_task(hub.install_firmware_update(poll_interval=0.001))
    await asyncio.sleep(0)

    with pytest.raises(FirmwareUpdateError) as raised:
        await hub.install_firmware_update(poll_interval=0.001)

    assert raised.value.reason is FirmwareUpdateErrorReason.UPDATE_ALREADY_IN_PROGRESS
    first_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await first_task
