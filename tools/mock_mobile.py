#!/usr/bin/env python3
import argparse
import asyncio
import io
import json
import time

from PIL import Image, ImageDraw, ImageFont
import websockets


def make_frame(width: int, height: int, counter: int) -> bytes:
    image = Image.new("RGB", (width, height), color=(20, 20, 20))
    draw = ImageDraw.Draw(image)
    timestamp = time.strftime("%H:%M:%S")
    text = f"Mock Mobile Frame {counter}\n{timestamp}"
    draw.multiline_text((20, 20), text, fill=(255, 255, 255))

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=80)
    return buffer.getvalue()


async def stream(uri: str, fps: int, width: int, height: int):
    interval = 1.0 / fps
    counter = 0
    async with websockets.connect(uri, max_size=10 * 1024 * 1024) as websocket:
        async def _produce():
            nonlocal counter
            while True:
                payload = make_frame(width, height, counter)
                await websocket.send(payload)
                await asyncio.sleep(interval)
                counter += 1

        async def _consume():
            async for message in websocket:
                if isinstance(message, str):
                    try:
                        payload = json.loads(message)
                        print(f"Control received: {payload}")
                    except json.JSONDecodeError:
                        print(f"Control received (raw): {message}")

        await asyncio.gather(_produce(), _consume())


def parse_args():
    parser = argparse.ArgumentParser(description="Mock mobile screen sender")
    parser.add_argument("--ws", default="ws://localhost:8765/sender")
    parser.add_argument("--fps", type=int, default=10)
    parser.add_argument("--width", type=int, default=720)
    parser.add_argument("--height", type=int, default=1280)
    return parser.parse_args()


def main():
    args = parse_args()
    asyncio.run(stream(args.ws, args.fps, args.width, args.height))


if __name__ == "__main__":
    main()
