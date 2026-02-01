---
phase: 5
plan: 1
wave: 1
gap_closure: true
---

# Plan 5.1: Test Suite Modernization

## Objective
Repair regressions in legacy UI logic tests caused by the v0.8.0 structural changes and synchronize the parameter wiring registry to prevent future signature drift.

## Context
- `tests/test_ui_logic.py` (Currently failing)
- `tests/test_ui_wiring.py` (Outdated)
- `wildcards_gen/gui.py` (Reference for signature)

## Tasks

<task type="auto">
  <name>Repair UI Logic Tests</name>
  <files>
    - /home/tazztone/_coding/wildcards-gen/tests/test_ui_logic.py
  </files>
  <action>
    Update `test_on_dataset_change_resets_analysis` to expect 6 items instead of 8.
    Remove assertions for the obsolete analysis_stats and apply_row updates.
  </action>
  <verify>`uv run pytest tests/test_ui_logic.py`</verify>
  <done>UI logic tests pass with the new optimized return structure.</done>
</task>

<task type="auto">
  <name>Synchronize UI Wiring Registry</name>
  <files>
    - /home/tazztone/_coding/wildcards-gen/tests/test_ui_wiring.py
  </files>
  <action>
    Update `expected_params` in `test_dataset_handler_wiring` to include the full list of ~30 parameters now present in `generate_dataset_handler`.
    This includes semantic tuning, UMAP/HDBSCAN parameters, and the new `fast_preview` flag.
  </action>
  <verify>`uv run pytest tests/test_ui_wiring.py`</verify>
  <done>UI wiring tests provide 100% parameter coverage for the dataset handler.</done>
</task>

## Success Criteria
- [ ] `tests/test_ui_logic.py` returns 0 failures.
- [ ] `tests/test_ui_wiring.py` returns 0 failures.
