# Change Note

- Date: 2026-02-12
- Commit: pending
- Scope: QtScrcpy wireless scan stability and ADB detection robustness

## 1) Problem / Symptom
- Wi-Fi scan could stay in scanning state for too long and sometimes not stop cleanly.
- Subnet selection could be inefficient, causing long scans when adapters are complex.
- Some environments showed false ADB warning even when `adb` was actually runnable.

## 2) Root Cause
- Scan sockets could be counted down more than once (timeout + socket error path), making active scan count inconsistent.
- Subnet selection only used current interface pass; there was no persisted fallback subnet strategy.
- `checkAdbVersion()` only checked stdout for the marker string; some ADB builds may report version text differently.

## 3) Changes Made
- `QtScrcpy/src/adb/devicediscovery.cpp`
  - Added guarded decrement logic for socket lifecycle, and clamped active scan counter to avoid negative values.
  - Disconnected socket signals before abort during stop/timeout cleanup to prevent duplicate callbacks.
  - Updated finish condition to accept `m_activeScans <= 0`.
  - Added subnet strategy:
    - active Wi-Fi subnet first,
    - last successful saved subnet fallback,
    - configured wireless fallback,
    - active any-interface fallback.
  - Added local persistence of successful scan segments in `QSettings`.
- `QtScrcpy/src/adb/devicediscovery.h`
  - Added helpers and `activeScanSegments()` accessor.
- `QtScrcpy/src/adb/adbprocess.cpp`
  - Improved ADB version check to inspect combined stdout + stderr.
- `QtScrcpy/src/adb/devicemanager.cpp`
  - Start ADB daemon (`adb start-server`) before periodic polling.

## 4) Validation Evidence
- Code-level validation completed for modified paths and state transitions.
- Local full build is not executable in this environment because required Visual Studio/Ninja toolchain is unavailable here.
- CI build is expected to validate compile/package behavior after push.

## 5) Risk and Rollback
- Risk:
  - Slight behavior change in subnet selection order.
  - Saved subnet may choose prior known subnet when no active Wi-Fi is present.
- Rollback:
  - Revert this commit to restore previous scan and ADB behavior.
