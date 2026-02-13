# 2026-02-13 ADB devices retry + online-only filtering

## Background
- Runtime log (`f:/down/QtScrcpy-win-x64(23)/log.txt`) shows transient ADB daemon fault:
  - `adb.exe: failed to check server version: protocol fault (couldn't read status): connection reset`
- The same log also shows temporary Wi-Fi state flapping (`192.168.2.159:5555 offline`).

## Problem
- `getDevices()` previously treated `offline/unauthorized` as available devices.
- During transport transitions (USB <-> Wi-Fi), transient daemon faults could make one poll fail and increase UI instability.

## Changes
- File: `QtScrcpy/src/adb/adbprocess.cpp`
- In `AdbProcess::getDevices()`:
  - Add one automatic retry path for known transient daemon errors (`protocol fault`, `connection reset`, `failed to check server version`, `daemon not running`) by running `start-server` then re-running `devices`.
  - Parse only entries in `device` state as connectable devices; exclude `offline` and `unauthorized` from returned serial list.

## Expected effect
- Reduce "no response" windows caused by transient ADB daemon state.
- Avoid promoting offline endpoints into active device list, which lowers false-positive connectability and reduces state jitter.
