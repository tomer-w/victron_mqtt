"""Token-based MQTT pairing with Victron GX devices."""

import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)


class PairingError(Exception):
    """Raised when token pairing with the GX device fails."""


async def request_pairing_token(
    host: str,
    device_id: str,
    session: aiohttp.ClientSession,
    *,
    role: str = "homeassistant",
) -> dict[str, str]:
    """Request MQTT pairing credentials from a GX device via HTTPS.

    The GX device must have pairing mode enabled. On success the device
    returns credentials that grant exclusive MQTT broker access. If MQTT
    Access was turned off, it will change to "Paired devices only"
    automatically.

    Args:
        host: Hostname or IP of the GX device.
        device_id: Unique identifier for this client (e.g. installation_id).
        session: An aiohttp ClientSession (caller controls SSL verification).
        role: Role name sent to the GX device (default: "homeassistant").

    Returns:
        A dict with "token_name" and "password" keys.

    Raises:
        PairingError: The GX device rejected the pairing request.
        aiohttp.ClientError: Network-level failure.

    """
    url = f"https://{host}/auth/generate-token/"
    resp = await session.post(
        url,
        data={"role": role, "device_id": device_id},
    )
    if resp.status != 200:
        body = await resp.text()
        _LOGGER.error(
            "Token pairing request failed (HTTP %s): %s", resp.status, body
        )
        raise PairingError(f"HTTP {resp.status}: {body}")
    result: dict[str, Any] = await resp.json(content_type=None)
    _LOGGER.debug("Token pairing successful, token_name=%s", result.get("token_name"))
    return result
