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

## Testing note

If a change lists "Testing: 未运行（未要求）", it means no automated tests were executed for that change because none were requested.

## Run the mirror server

```bash
python app/mirror_server.py
```

The web viewer is served at `http://localhost:8000` and will connect to the WebSocket server on port `8765`.

## Windows EXE build (no adb)

The following creates a single-file Windows EXE that launches the server and opens the viewer page.

```bash
pip install pyinstaller
pyinstaller --onefile --name MirrorView app/launcher.py
```

After packaging, the executable is located at `dist/MirrorView.exe`.

## GitHub Actions EXE build

The repository includes a GitHub Actions workflow that builds `MirrorView.exe` on Windows and uploads it as a workflow artifact.


## Run the mock mobile sender

```bash
python tools/mock_mobile.py --ws ws://localhost:8765/sender
```

Open `http://localhost:8000` in a browser to see the mirrored frames.

## Next steps

- Replace the mock sender with a real mobile capture pipeline.
- Add authentication and encryption.
- Introduce adaptive bitrate and frame pacing.
