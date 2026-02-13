# Change Note

- Date: 2026-02-13
- Commit: pending
- Scope: smoothness stabilization and fullscreen adaptation polish

## 1) Problem / Symptom
- User reported next target after IME/audio success: improve smoothness and fullscreen display adaptation.
- Existing render path requested `update()` for every incoming frame; at high frame rates this can cause repaint burst/jitter on some PCs.
- Fullscreen toggle only switched window state; menu/status/toolbar remained visible, reducing effective video area and causing poor fullscreen fit experience.

## 2) Root Cause
- Repaint scheduling was unbounded by presentation cadence, so GUI thread could receive redundant paint requests under burst frame input.
- Fullscreen UX state was not coordinated at MainWindow level (chrome visibility and return-to-list recovery).
- Keyboard F11/Esc toggled fullscreen inside `VideoWidget`, bypassing MainWindow fullscreen UI coordination.

## 3) Changes Made
- `QtScrcpy/src/ui/videowidget.h`
  - Added lightweight present-throttle state:
    - `m_targetFrameIntervalMs` (16ms target)
    - `m_presentTimer`
- `QtScrcpy/src/ui/videowidget.cpp`
  - `updateFrame()` now coalesces excessive repaint requests to roughly display cadence while always keeping latest frame.
  - `setFullScreen()` now immediately refreshes input mapping display size after render-rect updates.
  - `keyPressEvent()` F11/Esc now emits `doubleClicked()` so MainWindow handles fullscreen state uniformly.
- `QtScrcpy/src/ui/mainwindow.cpp`
  - `onFullscreenClicked()` now toggles window chrome visibility:
    - menu bar, status bar, toolbar hidden in fullscreen and restored on exit.
  - On fullscreen toggle, re-run `resizeToFit()` for better frame fit.
  - `showDeviceList()` now always restores normal fullscreen/chrome state to prevent UI getting stuck hidden after disconnect.

## 4) Validation Evidence
- Source checks confirm:
  - repaint cadence logic exists and no longer blindly calls `update()` per frame.
  - fullscreen enter/exit updates chrome visibility and re-fit behavior.
  - F11/Esc path now routes through MainWindow fullscreen handler.
- Expected user-visible effect:
  - steadier visual smoothness under high incoming frame rate,
  - larger effective fullscreen video area with cleaner fit,
  - consistent fullscreen behavior across toolbar/menu/F11/Esc/double-click paths.

## 5) Risk and Rollback
- Risk:
  - Aggressive cadence cap may slightly increase frame drop on very high FPS sources.
- Rollback:
  - Revert this commit to restore previous per-frame immediate repaint and old fullscreen chrome behavior.
