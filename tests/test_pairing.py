"""Tests for the GX device MQTT token pairing function."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from victron_mqtt.pairing import PairingError, PairingToken, request_pairing_token


def _mock_session(*, status: int = 200, json_data: dict[str, Any] | None = None, text: str = ""):
    """Build a mock aiohttp.ClientSession whose .post() returns a fake response."""
    resp = AsyncMock()
    resp.status = status
    resp.json = AsyncMock(return_value=json_data)
    resp.text = AsyncMock(return_value=text)

    session = MagicMock()
    session.post = AsyncMock(return_value=resp)
    return session


def _patch_client_session(session: MagicMock):
    """Patch aiohttp.ClientSession to return *session* as an async context manager."""
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return patch("victron_mqtt.pairing.aiohttp.ClientSession", return_value=ctx)


# -- successful pairing ------------------------------------------------


@pytest.mark.asyncio
async def test_successful_pairing_returns_credentials():
    """A 200 response with token_name + password is returned as a PairingToken."""
    payload = {
        "token_name": "token/homeassistant/ab4c9ab6b98a",
        "password": "Km7rPx4QjW9vBn2sYdLe6TfHc8gAoU3Z",
    }
    session = _mock_session(status=200, json_data=payload)

    with _patch_client_session(session):
        result = await request_pairing_token("192.168.1.10", "ab4c9ab6b98a")

    assert isinstance(result, PairingToken)
    assert result.token_name == "token/homeassistant/ab4c9ab6b98a"
    assert result.password == "Km7rPx4QjW9vBn2sYdLe6TfHc8gAoU3Z"


@pytest.mark.asyncio
async def test_successful_pairing_posts_to_correct_url():
    """The request targets https://<host>/auth/generate-token/."""
    session = _mock_session(status=200, json_data={
        "token_name": "token/homeassistant/c7e2f03d81a5",
        "password": "Rn5tGx8WqJ3vKm7ePd2sYfLb6HcAoU9Z"
    })

    with _patch_client_session(session):
        await request_pairing_token("venus.local", "c7e2f03d81a5")

    session.post.assert_called_once_with(
        "https://venus.local/auth/generate-token/",
        data={"role": "homeassistant", "device_id": "c7e2f03d81a5"},
    )


@pytest.mark.asyncio
async def test_successful_pairing_with_custom_role():
    """A custom role is forwarded in the POST data."""
    session = _mock_session(status=200, json_data={
        "token_name": "token/custom_role/d9f1a47e52b3",
        "password": "Vc3nFx7WqJ9tKm2ePd5sYgLb8HcAoU6Z"
    })

    with _patch_client_session(session):
        await request_pairing_token("10.0.0.1", "d9f1a47e52b3", role="custom_role")

    session.post.assert_called_once_with(
        "https://10.0.0.1/auth/generate-token/",
        data={"role": "custom_role", "device_id": "d9f1a47e52b3"},
    )


@pytest.mark.asyncio
async def test_successful_pairing_extended_response():
    """Extra fields in the GX response are ignored; only token_name and password are kept."""
    payload = {
        "token_name": "token/homeassistant/e8b3d2f71a06",
        "password": "Ht4nQx9WrJ2vKm7ePd3sYfLb5GcAoU8Z",
        "mqtt_host": "192.168.1.10",
        "mqtt_port": 8883,
        "mqtt_ssl": True,
    }
    session = _mock_session(status=200, json_data=payload)

    with _patch_client_session(session):
        result = await request_pairing_token("192.168.1.10", "e8b3d2f71a06")

    assert isinstance(result, PairingToken)
    assert result.token_name == "token/homeassistant/e8b3d2f71a06"
    assert result.password == "Ht4nQx9WrJ2vKm7ePd3sYfLb5GcAoU8Z"


# -- failure cases -----------------------------------------------------


@pytest.mark.asyncio
async def test_non_alphanumeric_device_id_raises_value_error():
    """A device_id with non-alphanumeric characters is rejected before any HTTP call."""
    with pytest.raises(ValueError, match="alphanumeric"):
        await request_pairing_token("192.168.1.10", "bad-id!")


@pytest.mark.asyncio
async def test_403_raises_pairing_error():
    """A 403 (pairing mode not enabled) raises PairingError."""
    session = _mock_session(status=403, text="Pairing mode not enabled")

    with _patch_client_session(session), pytest.raises(PairingError, match="HTTP 403"):
        await request_pairing_token("192.168.1.10", "abc")


@pytest.mark.asyncio
async def test_500_raises_pairing_error():
    """A server error raises PairingError with status and body."""
    session = _mock_session(status=500, text="Internal Server Error")

    with _patch_client_session(session), pytest.raises(PairingError, match=r"HTTP 500.*Internal Server Error"):
        await request_pairing_token("192.168.1.10", "abc")


@pytest.mark.asyncio
async def test_401_raises_pairing_error():
    """An unauthorized response raises PairingError."""
    session = _mock_session(status=401, text="Unauthorized")

    with _patch_client_session(session), pytest.raises(PairingError, match="HTTP 401"):
        await request_pairing_token("192.168.1.10", "abc")


@pytest.mark.asyncio
async def test_network_error_propagates():
    """An aiohttp connection error is not caught and propagates to the caller."""
    session = MagicMock()
    session.post = AsyncMock(side_effect=aiohttp.ClientConnectorError(
        connection_key=MagicMock(), os_error=OSError("Connection refused"),
    ))

    with _patch_client_session(session), pytest.raises(aiohttp.ClientError):
        await request_pairing_token("192.168.1.10", "abc")
