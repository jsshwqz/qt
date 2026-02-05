import asyncio
import socket
import subprocess
import sys
import time

import websockets


def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _start_server(http_port: int, ws_port: int) -> subprocess.Popen:
    return subprocess.Popen(
        [
            sys.executable,
            "app/mirror_server.py",
            "--host",
            "127.0.0.1",
            "--http-port",
            str(http_port),
            "--ws-port",
            str(ws_port),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def _stop_process(process: subprocess.Popen) -> None:
    process.terminate()
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()


def test_end_to_end_stream_and_control():
    http_port = _get_free_port()
    ws_port = _get_free_port()
    server = _start_server(http_port, ws_port)

    async def _exercise():
        sender_uri = f"ws://127.0.0.1:{ws_port}/sender"
        viewer_uri = f"ws://127.0.0.1:{ws_port}/viewer"
        control_uri = f"ws://127.0.0.1:{ws_port}/control"

        for _ in range(30):
            try:
                async with websockets.connect(sender_uri):
                    break
            except OSError:
                await asyncio.sleep(0.1)
        else:
            raise RuntimeError("WebSocket server did not start")

        async with websockets.connect(sender_uri, max_size=10 * 1024 * 1024) as sender_ws:
            await sender_ws.send(b"frame-bytes")

            async with websockets.connect(viewer_uri, max_size=10 * 1024 * 1024) as viewer_ws:
                payload = await asyncio.wait_for(viewer_ws.recv(), timeout=5)
                assert isinstance(payload, (bytes, bytearray))
                assert payload == b"frame-bytes"

            async with websockets.connect(control_uri, max_size=10 * 1024 * 1024) as control_ws:
                await control_ws.send('{"type":"tap","x":10,"y":20}')

            control_message = await asyncio.wait_for(sender_ws.recv(), timeout=5)
            assert control_message == '{"type":"tap","x":10,"y":20}'

    try:
        asyncio.run(_exercise())
    finally:
        _stop_process(server)
        if server.stdout:
            server.stdout.close()

