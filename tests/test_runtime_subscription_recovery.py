"""Runtime subscription recovery using a real Paho thread and a loopback broker."""

import asyncio
import contextlib
from unittest.mock import patch

import pytest

from victron_mqtt import Hub


def _packet(command: int, payload: bytes = b"") -> bytes:
    length = len(payload)
    remaining = bytearray()
    while True:
        digit = length % 128
        length //= 128
        remaining.append(digit | (128 if length else 0))
        if not length:
            return bytes([command]) + remaining + payload


async def _read_packet(reader: asyncio.StreamReader) -> tuple[int, bytes]:
    command = (await reader.readexactly(1))[0]
    length = 0
    shift = 0
    while True:
        digit = (await reader.readexactly(1))[0]
        length |= (digit & 127) << shift
        shift += 7
        if not digit & 128:
            return command >> 4, await reader.readexactly(length)


@pytest.mark.asyncio
@pytest.mark.parametrize("withhold_ack", [False, True])
async def test_runtime_suback_recovery_with_real_paho(withhold_ack: bool) -> None:
    """A missing reconnect SUBACK recovers without killing Paho's network loop."""
    sessions: list[list[int]] = []
    writers: set[asyncio.StreamWriter] = set()
    handlers: set[asyncio.Task[None]] = set()

    async def broker(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        task = asyncio.current_task()
        assert task is not None
        handlers.add(task)
        writers.add(writer)
        subscriptions: list[int] = []
        sessions.append(subscriptions)
        session = len(sessions)
        try:
            while True:
                kind, data = await _read_packet(reader)
                if kind == 1:  # CONNECT
                    writer.write(_packet(0x20, b"\x00\x00"))
                elif kind == 8:  # SUBSCRIBE
                    offset = 2
                    count = 0
                    while offset < len(data):
                        size = int.from_bytes(data[offset : offset + 2], "big")
                        offset += size + 3
                        count += 1
                    subscriptions.append(count)
                    if withhold_ack and session == 2 and len(subscriptions) == 1:
                        continue
                    if withhold_ack and session == 2:
                        # A late ACK for the timed-out MID must not satisfy the retry.
                        old_mid = (int.from_bytes(data[:2], "big") - 1).to_bytes(2, "big")
                        writer.write(_packet(0x90, old_mid + bytes(count)))
                        await writer.drain()
                        await asyncio.sleep(0.01)
                    writer.write(_packet(0x90, data[:2] + bytes(count)))
                    if session == 1 and len(subscriptions) == 1:
                        topic = b"N/probe/system/0/Serial"
                        writer.write(_packet(0x30, len(topic).to_bytes(2, "big") + topic + b'{"value":"probe"}'))
                elif kind == 10:  # UNSUBSCRIBE
                    writer.write(_packet(0xB0, data[:2]))
                elif kind == 12:  # PINGREQ
                    writer.write(_packet(0xD0))
                elif kind == 14:  # DISCONNECT
                    break
                await writer.drain()
        except (asyncio.IncompleteReadError, ConnectionError):
            pass
        finally:
            writers.discard(writer)
            writer.close()
            with contextlib.suppress(ConnectionError):
                await writer.wait_closed()
            handlers.discard(task)

    server = await asyncio.start_server(broker, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    hub = Hub("127.0.0.1", port, None, None, False, installation_id="probe")
    hub._client.reconnect_delay_set(min_delay=1, max_delay=1)
    with patch("victron_mqtt.hub.SUBSCRIPTION_ACK_TIMEOUT_SECONDS", 0.2):
        try:
            await asyncio.wait_for(hub.connect(), timeout=5)
            assert len(sessions) == 1
            assert len(sessions[0]) == 2
            for writer in tuple(writers):
                writer.transport.abort()

            async with asyncio.timeout(5):
                while len(sessions) < 2 or hub._subscription_task is None or not hub._subscription_task.done():
                    await asyncio.sleep(0.01)
            await hub._subscription_task
            assert hub.connected
            assert hub._client._thread is not None
            assert hub._client._thread.is_alive()
            assert len(sessions) == 2
            assert len(sessions[1]) == (2 if withhold_ack else 1)
            assert all(count == sessions[0][1] for count in sessions[1])
            assert hub._pending_subscription is None
        finally:
            try:
                await hub.disconnect()
            finally:
                server.close()
                await server.wait_closed()
                for writer in tuple(writers):
                    writer.close()
                if handlers:
                    await asyncio.gather(*handlers)
    assert not hub.connected
    assert hub._client._thread is None
