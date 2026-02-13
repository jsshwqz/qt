# Change Note

- Date: 2026-02-13
- Commit: pending
- Scope: Android 10 and below audio recovery via sndcpy fallback + packaging guard

## 1) Problem / Symptom
- Devices could mirror video/control but had no PC audio on Android 10-class phones.
- Previous package did not guarantee `sndcpy.apk` was present in the release asset.

## 2) Root Cause
- Current runtime only enabled scrcpy native audio (`audio=true`, raw PCM socket) for SDK >= 30.
- For SDK < 30, runtime disabled audio but had no automatic fallback path to start sndcpy service.
- CI packaging did not hard-require or copy `sndcpy.apk`, so fallback artifacts could be missing.

## 3) Changes Made
- `QtScrcpy/src/server/servermanager.h`
  - Added sndcpy fallback members/methods and constants.
- `QtScrcpy/src/server/servermanager.cpp`
  - Added SDK-based audio strategy:
    - SDK >= 30: keep scrcpy audio path.
    - SDK 1..29: enable sndcpy fallback.
  - Added `sndcpy.apk` discovery (`appDir/sndcpy.apk` then `appDir/resources/sndcpy.apk`).
  - Added fallback preparation before server start:
    - detect/install `com.rom1v.sndcpy` (`adb install -t -r -g`).
  - Added fallback activation during port-forward stage:
    - forward `tcp:<audioPort>` to `localabstract:sndcpy`.
    - run `appops set ... PROJECT_MEDIA allow` and start activity.
    - poll process readiness (`pidof` / `ps | grep`).
  - If fallback setup fails, downgrade gracefully to video/control-only without aborting connection.
  - On disconnect/stop, force-stop sndcpy package for session cleanup.
- `.github/workflows/build-windows.yml`
  - Enforced presence of `QtScrcpy/resources/sndcpy.apk`.
  - Copied `sndcpy.apk` into build output and release package.
  - Added package-level validation and runtime summary visibility for `sndcpy.apk`.
- `QtScrcpy/resources/sndcpy.apk`
  - Added fallback runtime asset to source tree for deterministic packaging.

## 4) Validation Evidence
- Static verification:
  - `ServerManager` now contains explicit sndcpy fallback branches, install/start checks, and cleanup.
  - Workflow now fails fast when `sndcpy.apk` is missing and verifies packaged presence.
- Expected runtime behavior:
  - Android 11+: unchanged scrcpy audio behavior.
  - Android 10 and below: audio attempts through sndcpy fallback; if unavailable, session still keeps video/control.

## 5) Risk and Rollback
- Risks:
  - Some OEM ROMs may block `PROJECT_MEDIA` appops or background launch; fallback may downgrade to no-audio.
  - First-time install/start of sndcpy adds connection latency.
- Rollback:
  - Revert this note's corresponding commit to restore prior SDK>=30-only audio behavior.
