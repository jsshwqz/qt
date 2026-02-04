#!/usr/bin/env python3
import argparse
import asyncio
import io
import json
import queue
import threading
import tkinter as tk
from dataclasses import dataclass
from typing import Optional

from PIL import Image, ImageTk
from websockets import connect


@dataclass
class ControlMessage:
    type: str
    x: float
    y: float


class ViewerClient:
    def __init__(self, viewer_ws: str, control_ws: str):
        self.viewer_ws = viewer_ws
        self.control_ws = control_ws
        self.frame_queue: queue.Queue[bytes] = queue.Queue()
        self._control_queue: asyncio.Queue[str] = asyncio.Queue()
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.create_task(self._consume_frames())
        self._loop.create_task(self._send_controls())
        self._loop.run_forever()

    async def _consume_frames(self):
        while True:
            try:
                async with connect(self.viewer_ws, max_size=10 * 1024 * 1024) as ws:
                    async for message in ws:
                        if isinstance(message, (bytes, bytearray)):
                            self.frame_queue.put(bytes(message))
            except Exception:
                await asyncio.sleep(1)

    async def _send_controls(self):
        while True:
            try:
                async with connect(self.control_ws) as ws:
                    while True:
                        payload = await self._control_queue.get()
                        await ws.send(payload)
            except Exception:
                await asyncio.sleep(1)

    def send_control(self, message: ControlMessage):
        payload = json.dumps(message.__dict__)

        def _enqueue():
            self._control_queue.put_nowait(payload)

        self._loop.call_soon_threadsafe(_enqueue)


class DesktopViewerApp:
    def __init__(self, root: tk.Tk, client: ViewerClient, refresh_ms: int = 50):
        self.root = root
        self.client = client
        self.refresh_ms = refresh_ms
        self.label = tk.Label(root)
        self.label.pack(fill=tk.BOTH, expand=True)
        self._photo: Optional[ImageTk.PhotoImage] = None
        self.label.bind("<Button-1>", self._on_click)
        self.root.after(self.refresh_ms, self._poll_frames)

    def _on_click(self, event):
        if not self._photo:
            return
        width = self.label.winfo_width() or 1
        height = self.label.winfo_height() or 1
        x = max(0.0, min(1.0, event.x / width))
        y = max(0.0, min(1.0, event.y / height))
        self.client.send_control(ControlMessage(type="tap", x=x, y=y))

    def _poll_frames(self):
        frame_data = None
        while not self.client.frame_queue.empty():
            frame_data = self.client.frame_queue.get()
        if frame_data:
            image = Image.open(io.BytesIO(frame_data)).convert("RGB")
            self._photo = ImageTk.PhotoImage(image)
            self.label.configure(image=self._photo)
        self.root.after(self.refresh_ms, self._poll_frames)


def parse_args():
    parser = argparse.ArgumentParser(description="Desktop viewer for mirror frames")
    parser.add_argument("--viewer-ws", default="ws://127.0.0.1:8765/viewer")
    parser.add_argument("--control-ws", default="ws://127.0.0.1:8765/control")
    return parser.parse_args()


def main():
    args = parse_args()
    root = tk.Tk()
    root.title("MirrorView Desktop")
    client = ViewerClient(args.viewer_ws, args.control_ws)
    DesktopViewerApp(root, client)
    root.mainloop()


if __name__ == "__main__":
    main()
