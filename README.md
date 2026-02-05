# Mobile Screen Mirroring (Prototype)

This prototype provides a lightweight relay server and viewer for mirroring a mobile screen. It includes:

- A WebSocket relay server that accepts binary frames from a sender.
- A simple web viewer that displays the most recent frame and basic stream metrics.
- A mock sender script that simulates a mobile device stream.

## Requirements

- Python 3.10+
- `websockets`
- `Pillow`

```bash
pip install -r requirements.txt
```

## Testing

Install test dependencies and run the automated end-to-end test (stream + control) with:

```bash
pip install -r requirements.txt pytest
pytest -q
```

The GitHub Actions workflow runs the same test suite on every push to `main`.

## Testing requirement (global)

Every code change must run the automated tests before committing. The expected command is:

```bash
pytest -q
```

## Run the mirror server

```bash
python app/mirror_server.py
```

The web viewer is served at `http://localhost:8000` and will connect to the WebSocket server on port `8765`.

## Desktop viewer (no browser)

Use the desktop viewer to display frames without opening a browser window.

```bash
python app/desktop_viewer.py --viewer-ws ws://127.0.0.1:8765/viewer --control-ws ws://127.0.0.1:8765/control
```

Click on the window to send tap control messages through the `/control` WebSocket.

## Windows EXE build (no adb)

The following creates a single-file Windows EXE that launches the server and opens the viewer page.

```bash
pip install pyinstaller
pyinstaller --onefile --name MirrorView app/launcher.py
```

After packaging, the executable is located at `dist/MirrorView.exe`.

## GitHub Actions EXE build

The repository includes a GitHub Actions workflow that builds `MirrorView.exe` on Windows and uploads it as a workflow artifact.

The workflow also publishes a GitHub Release containing `MirrorView.exe` automatically after each run.
The Release uses the fixed tag `MirrorView-latest` and includes a `MirrorView.exe.sha256` checksum file for verification.


## Run the mock mobile sender

```bash
python tools/mock_mobile.py --ws ws://localhost:8765/sender
```

Open `http://localhost:8000` in a browser to see the mirrored frames.

## Next steps

- Replace the mock sender with a real mobile capture pipeline.
- Add authentication and encryption.
- Introduce adaptive bitrate and frame pacing.
