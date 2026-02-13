# Change Note

- Date: 2026-02-13
- Commit: pending
- Scope: Fullscreen usability (keep mouse cursor visible)

## 1) Problem / Symptom
- In fullscreen mode, mouse pointer disappeared.
- Users could not accurately locate text input fields/click targets on device screen.

## 2) Root Cause
- `VideoWidget::setFullScreen(true)` explicitly set cursor to `Qt::BlankCursor`.
- This forced cursor hiding on desktop even during interactive control scenarios.

## 3) Changes Made
- `QtScrcpy/src/ui/videowidget.cpp`
  - In fullscreen branch, changed cursor behavior from hidden to visible:
    - `Qt::BlankCursor` -> `Qt::ArrowCursor`
  - Keep non-fullscreen branch unchanged (`Qt::ArrowCursor`).

## 4) Validation Evidence
- Source-level verification:
  - fullscreen path no longer sets blank cursor.
  - both fullscreen/non-fullscreen use visible arrow cursor.
- Expected behavior:
  - entering fullscreen retains pointer visibility for precise positioning and typing.

## 5) Risk and Rollback
- Known risk:
  - no major functional risk; only pointer visibility policy changed.
- Rollback plan:
  - revert this commit to restore hidden-cursor fullscreen behavior.

