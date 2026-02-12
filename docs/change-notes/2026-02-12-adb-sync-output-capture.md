# Change Note

- Date: 2026-02-12
- Commit: pending
- Scope: stabilize ADB output capture in synchronous command path

## 1) Problem / Symptom
- ADB commands were successful on command line, but QtScrcpy still showed no device in UI.
- This could happen even after parsing improvements for whitespace-separated `adb devices` output.

## 2) Root Cause
- `AdbProcess::execute()` read process output only from `readAllStandardOutput/Error()` after `waitForFinished()`.
- The same `QProcess` instance also had `readyRead...` slots attached, which can consume output into `m_stdOutput/m_stdError` before final `readAll...`.
- In that case, `execute()` could return empty `result.output`, so device parsing saw no rows.

## 3) Changes Made
- `QtScrcpy/src/adb/adbprocess.cpp`
  - `execute()` now merges:
    - buffered slot content (`m_stdOutput/m_stdError`)
    - remaining unread bytes (`readAllStandardOutput/Error`)
  - `result.success` now also requires `QProcess::NormalExit`.
  - `getDevices()` now parses from combined `stdout + stderr` text to tolerate daemon startup banners.

## 4) Validation Evidence
- Static verification confirms sync path no longer loses command text when `readyRead` handlers are active.
- Combined parser path now reads the same textual stream users see in shell (including daemon startup lines).

## 5) Risk and Rollback
- Risk:
  - Low; output capture is additive and deterministic.
- Rollback:
  - Revert this commit to restore previous sync capture behavior.
