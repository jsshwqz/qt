#!/usr/bin/env python3
import argparse
import asyncio
import http.server
import os
import socketserver
import threading
from typing import Set

from websockets.legacy.server import WebSocketServerProtocol, serve

WEB_ROOT = os.path.join(os.path.dirname(__file__), "..", "web")


class QuietHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        return


def start_http_server(host: str, port: int) -> socketserver.TCPServer:
    handler = QuietHTTPRequestHandler
    handler.directory = os.path.abspath(WEB_ROOT)
    httpd = socketserver.TCPServer((host, port), handler)

    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd


async def stream_handler(
    websocket: WebSocketServerProtocol,
    path: str,
    viewers: Set[WebSocketServerProtocol],
    state: dict,
):
    if path == "/viewer":
        viewers.add(websocket)
        try:
            last_frame = state.get("last_frame")
            if last_frame:
                await websocket.send(last_frame)
            await websocket.wait_closed()
        finally:
            viewers.discard(websocket)
        return

    if path != "/sender":
        await websocket.close(code=1008, reason="Unsupported path")
        return

    async for message in websocket:
        if not isinstance(message, (bytes, bytearray)):
            continue
        state["last_frame"] = message
        if not viewers:
            continue
        await asyncio.gather(
            *[viewer.send(message) for viewer in list(viewers) if viewer.open],
            return_exceptions=True,
        )


async def start_ws_server(host: str, port: int):
    viewers: Set[WebSocketServerProtocol] = set()
    state = {"last_frame": None}
    async with serve(
        lambda ws, path: stream_handler(ws, path, viewers, state),
        host,
        port,
        max_size=10 * 1024 * 1024,
    ):
        await asyncio.Future()


def parse_args():
    parser = argparse.ArgumentParser(description="Simple mobile screen mirroring relay server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--http-port", type=int, default=8000)
    parser.add_argument("--ws-port", type=int, default=8765)
    return parser.parse_args()


def main():
    args = parse_args()
    httpd = start_http_server(args.host, args.http_port)
    print(f"HTTP server running at http://{args.host}:{args.http_port}")
    print(f"WebSocket server running at ws://{args.host}:{args.ws_port}")

    try:
        asyncio.run(start_ws_server(args.host, args.ws_port))
    finally:
        httpd.shutdown()


if __name__ == "__main__":
    main()
