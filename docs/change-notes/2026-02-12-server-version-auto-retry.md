# Change Note

- Date: 2026-02-12
- Commit: pending
- Scope: auto-recover scrcpy server/client version mismatch during connect

## 1) Problem / Symptom
- Device list could show USB/Wi-Fi devices, but connect immediately failed with disconnect popup.
- Runtime log showed:
  - `The server version (3.3.4) does not match the client (2.4)`

## 2) Root Cause
- `ServerManager::buildServerArgs()` always sent hardcoded client version `2.4`.
- Bundled `scrcpy-server` in package was newer (`3.3.4`), so server exited.
- Startup flow also used a timed `serverReady` trigger, which could falsely announce readiness after server already failed.

## 3) Changes Made
- `QtScrcpy/src/server/servermanager.cpp`
  - Added mismatch detection in `onServerOutput()` using regex:
    - `server version (...) does not match the client (...)`
  - On first mismatch:
    - updates client version marker to server-reported version
    - restarts server process automatically (no user action).
  - Added one-shot retry guard to avoid infinite restart loops.
  - Added startup attempt id guard so delayed `serverReady` callback cannot fire for stale/failed attempt.
  - `buildServerArgs()` now uses `m_clientVersion` instead of hardcoded `2.4`.
- `QtScrcpy/src/server/servermanager.h`
  - Added retry/version state members and mismatch handler declaration.

## 4) Validation Evidence
- Log-based root cause directly matched by new regex handler.
- New flow prevents stale attempt from emitting `serverReady`.

## 5) Risk and Rollback
- Risk:
  - If server emits a similarly worded non-fatal message, retry may trigger once.
- Rollback:
  - Revert this commit to return to fixed-version launch behavior.
