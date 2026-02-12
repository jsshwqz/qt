# 2026-02-12 Server Stop Error Suppression

- Date: 2026-02-12
- Commit: pending (this note is committed with the fix)
- Scope: Runtime lifecycle handling around server process stop/disconnect

## 1) Problem / Symptom
- User feedback showed connection interruption popups with `Server process error: Process crashed` after stream disconnect.
- In disconnect scenarios, users could receive redundant or misleading error dialogs even when the app was already returning to device list.

## 2) Root Cause
- `ServerManager::stop()` always killed the process directly without blocking process signals, so `QProcess::errorOccurred` could still fire during intentional shutdown.
- `ServerManager::onServerError()` did not guard against `Stopping/Idle` states, so intentional shutdown path could be reported as a crash.
- `MainWindow::onServerError()` always showed a critical dialog, including stale callbacks arriving after disconnect state had already been cleared.

## 3) Changes Made
- `QtScrcpy/src/server/servermanager.cpp`
  - `stop()` now sets state to `Stopping`, blocks process signals, then uses graceful terminate -> kill fallback.
  - `onServerError()` now ignores callbacks in `Stopping/Idle` states.
  - `onServerError()` message normalized to `Server process error: <reason>`.
- `QtScrcpy/src/ui/mainwindow.cpp`
  - `onServerError()` now ignores stale server errors when already disconnected (`!m_isConnected && m_currentSerial.isEmpty()`).

## 4) Validation Evidence
- Source-level verification:
  - Confirmed state guard exists before emitting runtime error in `onServerError()`.
  - Confirmed stop path blocks process signals before terminate/kill.
  - Confirmed main window stale-error guard prevents duplicate popup path.
- Runtime log evidence used for diagnosis:
  - `F:\down\QtScrcpy-win-x64(12)\log.txt` shows disconnect sequence ending with:
    - `Video stream disconnected`
    - `Control stream disconnected`
    - `Server process error: "Process crashed"`
- Build/test:
  - Local compile was not executed in this environment (toolchain constraints).

## 5) Risk and Rollback
- Risk:
  - Real server process errors during active sessions remain visible; only stop/idle stale callbacks are suppressed.
- Rollback:
  - Revert this commit to restore previous stop/error behavior.
