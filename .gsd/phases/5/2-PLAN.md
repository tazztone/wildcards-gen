---
phase: 5
plan: 2
wave: 1
gap_closure: true
---

# Plan 5.2: Tooltip & Preset Validation

## Objective
Implement programmatic validation for educational tooltips and Smart Presets to ensure UX quality persists through future refactors.

## Context
- `wildcards_gen/gui.py`
- `.gsd/AUDIT.md`

## Tasks

<task type="auto">
  <name>Implement Registry Validation Test</name>
  <files>
    - /home/tazztone/_coding/wildcards-gen/tests/test_gui_registry.py
  </files>
  <action>
    Create a new test file that:
    1. Inspects the `smart_tuning_group` (and sub-accordions) in the UI.
    2. Verifies that every Slider and Checkbox has a non-empty `info` or `label` explaining its function.
    3. Verifies that `SMART_PRESETS` in `gui.py` still maps to valid values that match the component types (e.g., int values for Sliders).
  </action>
  <verify>`uv run pytest tests/test_gui_registry.py`</verify>
  <done>Educational metadata in the GUI is programmatically guarded against accidental deletion.</done>
</task>

## Success Criteria
- [ ] 100% tooltip coverage verified by test.
- [ ] Preset integrity verified by test.
