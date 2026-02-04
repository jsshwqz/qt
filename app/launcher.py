#!/usr/bin/env python3
import argparse
import asyncio

from app import mirror_server


def parse_args():
    parser = argparse.ArgumentParser(description="Launch mobile mirror server with browser")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--http-port", type=int, default=8000)
    parser.add_argument("--ws-port", type=int, default=8765)
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        asyncio.run(
            mirror_server.run_server(
                args.host,
                args.http_port,
                args.ws_port,
                open_browser=True,
            )
        )
    except Exception as exc:
        print("Failed to start mirror server:")
        print(exc)
        try:
            input("Press Enter to exit...")
        except EOFError:
            pass


if __name__ == "__main__":
    main()
