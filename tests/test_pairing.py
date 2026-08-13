"""Tests for the GX device MQTT token pairing function."""

from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from victron_mqtt.pairing import PairingError, request_pairing_token


def _mock_session(*, status: int = 200, json_data: dict | None = None, text: str = ""):
    """Build a mock aiohttp.ClientSession whose .post() returns a fake response."""
    resp = AsyncMock()
    resp.status = status
    resp.json = AsyncMock(return_value=json_data)
    resp.text = AsyncMock(return_value=text)

    session = MagicMock()
    session.post = AsyncMock(return_value=resp)
    return session


# -- successful pairing ------------------------------------------------


@pytest.mark.asyncio
async def test_successful_pairing_returns_credentials():
    """A 200 response with token_name + password is returned as-is."""
    payload = {
        "token_name": "homeassistant_abc123",
        "password": "s3cret-mqtt-p4ss",
    }
    session = _mock_session(status=200, json_data=payload)

    result = await request_pairing_token("192.168.1.10", "abc123", session)

    assert result == payload
    assert result["token_name"] == "homeassistant_abc123"
    assert result["password"] == "s3cret-mqtt-p4ss"


@pytest.mark.asyncio
async def test_successful_pairing_posts_to_correct_url():
    """The request targets https://<host>/auth/generate-token/."""
    session = _mock_session(status=200, json_data={"token_name": "t", "password": "p"})

    await request_pairing_token("venus.local", "device42", session)

    session.post.assert_called_once_with(
        "https://venus.local/auth/generate-token/",
        data={"role": "homeassistant", "device_id": "device42"},
    )


@pytest.mark.asyncio
async def test_successful_pairing_with_custom_role():
    """A custom role is forwarded in the POST data."""
    session = _mock_session(status=200, json_data={"token_name": "t", "password": "p"})

    await request_pairing_token("10.0.0.1", "dev1", session, role="custom_role")

    session.post.assert_called_once_with(
        "https://10.0.0.1/auth/generate-token/",
        data={"role": "custom_role", "device_id": "dev1"},
    )


@pytest.mark.asyncio
async def test_successful_pairing_extended_response():
    """The GX device may return extra fields; they are passed through."""
    payload = {
        "token_name": "homeassistant_xyz",
        "password": "p@ssw0rd",
        "mqtt_host": "192.168.1.10",
        "mqtt_port": 8883,
        "mqtt_ssl": True,
    }
    session = _mock_session(status=200, json_data=payload)

    result = await request_pairing_token("192.168.1.10", "xyz", session)

    assert result["token_name"] == "homeassistant_xyz"
    assert result["password"] == "p@ssw0rd"
    assert result["mqtt_host"] == "192.168.1.10"
    assert result["mqtt_port"] == 8883
    assert result["mqtt_ssl"] is True


# -- failure cases -----------------------------------------------------


@pytest.mark.asyncio
async def test_403_raises_pairing_error():
    """A 403 (pairing mode not enabled) raises PairingError."""
    session = _mock_session(status=403, text="Pairing mode not enabled")

    with pytest.raises(PairingError, match="HTTP 403"):
        await request_pairing_token("192.168.1.10", "abc", session)


@pytest.mark.asyncio
async def test_500_raises_pairing_error():
    """A server error raises PairingError with status and body."""
    session = _mock_session(status=500, text="Internal Server Error")

    with pytest.raises(PairingError, match="HTTP 500.*Internal Server Error"):
        await request_pairing_token("192.168.1.10", "abc", session)


@pytest.mark.asyncio
async def test_401_raises_pairing_error():
    """An unauthorized response raises PairingError."""
    session = _mock_session(status=401, text="Unauthorized")

    with pytest.raises(PairingError, match="HTTP 401"):
        await request_pairing_token("192.168.1.10", "abc", session)


@pytest.mark.asyncio
async def test_network_error_propagates():
    """An aiohttp connection error is not caught and propagates to the caller."""
    session = MagicMock()
    session.post = AsyncMock(side_effect=aiohttp.ClientConnectorError(
        connection_key=MagicMock(), os_error=OSError("Connection refused"),
    ))

    with pytest.raises(aiohttp.ClientError):
        await request_pairing_token("192.168.1.10", "abc", session)
