---
phase: 2
plan: 1
wave: 1
---

# Plan 2.1: UI Streamlining & Layout Rearrangement

## Objective
Remove obsolete UI elements and re-organize the CV Datasets tab into a balanced 2-column layout to reclaim space and improve focus.

## Context
- `wildcards_gen/gui.py`
- `wildcards_gen/custom.css` (if needed for layout tweaks)

## Tasks

<task type="auto">
  <name>Remove Obsolete Analysis Panels</name>
  <files>
    - /home/tazztone/_coding/wildcards-gen/wildcards_gen/gui.py
  </files>
  <action>
    1. Delete the `analysis_panel` Group and its children (`ds_analyze_btn`, `ds_apply_suggest`, `analysis_accordion`, `ds_analysis_stats`).
    2. Delete the `ds_history_view` and its associated state `history_state`.
    3. Update `analyze_handler` or any references to ensure no dead code crashes the UI.
  </action>
  <verify>Run `python -m wildcards_gen.gui` and confirm the Analysis section is gone.</verify>
  <done>Analysis and History sections are completely removed from the code and UI.</done>
</task>

<task type="auto">
  <name>Implement 2-Column Layout</name>
  <files>
    - /home/tazztone/_coding/wildcards-gen/wildcards_gen/gui.py
  </files>
  <action>
    Rearrange the "📸 CV Datasets" tab:
    1. Maintain the `sidebar` (Column scale 2).
    2. Simplify the right Column (scale 3):
       - Place the `ds_summary` (Status) at the top of the right column.
       - Place the `ds_prev` (YAML Preview) directly below it.
       - Group the `ds_btn` (Generate), `ds_fast_preview`, and `ds_file` (Download) at the bottom.
    3. Tighten padding and margins to ensure the interface fits well without scrolling.
  </action>
  <verify>Visual verification in browser.</verify>
  <done>Tab has a clear configuration (left) vs execution/preview (right) flow.</done>
</task>

## Success Criteria
- [ ] No "Analysis" or "History" code remains in Tab 1.
- [ ] Tab 1 layout is strictly two main columns.
- [ ] Vertical space is significantly reduced.
