---
phase: 3
plan: 1
wave: 1
---

# Plan 3.1: UX Polish & Educational Tooltips

## Objective
Improve the user experience by adding clear, educational `info` guidance to all Smart Tuning settings, enabling users to make informed decisions without referring to external documentation.

## Context
- `wildcards_gen/gui.py`

## Tasks

<task type="auto">
  <name>Enhance Smart Tuning Tooltips</name>
  <files>
    - /home/tazztone/_coding/wildcards-gen/wildcards_gen/gui.py
  </files>
  <action>
    Add or improve the `info` parameter for the following Gradio components:
    - `ds_min_depth`: "Keep categories shallower than this level regardless of descendant count (preserves top-level structure)."
    - `ds_min_hyponyms`: "Merge category if it has fewer than X descendants total."
    - `ds_min_leafSize`: "If a resulting list has fewer than X items, merge them into the parent node."
    - `ds_merge_orphans`: "Bubble up small lists into the parent's 'misc' or 'other' key instead of keeping them as separate categories."
    - `ds_semantic_clean`: "Use embeddings to remove items that don't belong in their category (requires local model)."
    - `ds_semantic_threshold`: "Higher = more aggressive cleaning (removes more potential outliers)."
    - `ds_umap_neighbors`: "Balances local vs global structure. Lower values focus on very tight details."
    - `ds_umap_dist`: "Determines how tight UMAP packs points. Lower = tighter clusters."
    - `ds_arr_samples`: "Minimum items required to form a new automated sub-category."
    - `ds_orphans_template`: "Custom label for miscellaneous items (e.g., 'misc {}' or 'other')."
  </action>
  <verify>Check GUI in browser; verify all tooltips are intuitive.</verify>
  <done>All Smart Tuning settings have professional, clear educational tooltips.</done>
</task>

## Success Criteria
- [ ] 100% coverage of Smart Tuning sliders/checkboxes with `info` text.
- [ ] No grammar or technical errors in tooltips.
