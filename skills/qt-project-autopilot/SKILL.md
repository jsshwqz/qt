---
name: qt-project-autopilot
description: Auto-harden this Qt/scrcpy project with zero-touch validation, disk-aware dependency handling, and cloud-build fallback when local installs are too heavy.
---

# Qt Project Autopilot

## When to use

Use this skill when you need to improve/maintain this project end-to-end without manual intervention:
- run validation
- fix obvious stability gaps
- prepare build
- avoid large local installs
- offload heavy build steps to `CloudBuild/`

## Workflow

1. Validate current state:
   - `python project_validator.py`

2. Run build in disk-friendly mode:
   - `python build_enhanced.py --cloud`

3. Read generated outputs:
   - `validation_report.json`
   - `project_validation.log`
   - `CloudBuild/cloud_build_request.json` (if cloud prep triggered)

4. If cloud prep exists, execute cloud pipeline from `CloudBuild/.github/workflows`.

## Notes

- This skill is designed for low-disk environments.
- It does not require installing >1GB local toolchains.
- It keeps cloud handoff artifacts reproducible inside `CloudBuild/`.
