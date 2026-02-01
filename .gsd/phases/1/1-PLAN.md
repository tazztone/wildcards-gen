---
phase: 1
plan: 1
wave: 1
---

# Plan 1.1: Fix Dataset Signatures & Add Tests

## Objective
Synchronize the dataset generation function signatures with the GUI's advanced tuning parameters and implement a regression test suite to prevent future mismatches.

## Context
- `.gsd/SPEC.md`
- `.gsd/phases/1/RESEARCH.md`
- `wildcards_gen/gui.py` (call site)
- `wildcards_gen/core/datasets/imagenet.py`
- `wildcards_gen/core/datasets/tencent.py`
- `wildcards_gen/core/datasets/openimages.py`

## Tasks

<task type="auto">
  <name>Synchronize Function Signatures</name>
  <files>
    - /home/tazztone/_coding/wildcards-gen/wildcards_gen/core/datasets/imagenet.py
    - /home/tazztone/_coding/wildcards-gen/wildcards_gen/core/datasets/tencent.py
    - /home/tazztone/_coding/wildcards-gen/wildcards_gen/core/datasets/openimages.py
  </files>
  <action>
    Update `generate_imagenet_tree`, `generate_tencent_hierarchy`, and `generate_openimages_hierarchy` to:
    1. Accept `umap_n_neighbors (int)`, `umap_min_dist (float)`, and `hdbscan_min_samples (Optional[int])` as typed arguments.
    2. Pass these arguments into the `SmartConfig` initialization within each function.
  </action>
  <verify>Check signatures using `inspect` module or visual check.</verify>
  <done>All three functions accept the new keyword arguments without error.</done>
</task>

<task type="auto">
  <name>Implement Signature Validation Test</name>
  <files>
    - /home/tazztone/_coding/wildcards-gen/tests/test_interface_sync.py
  </files>
  <action>
    Create a new test file that:
    1. Mocks the core dataset processing logic (to avoid actual downloads).
    2. Dynamically calls each dataset generator with the `kwargs` dictionary used in `gui.py:generate_dataset_handler`.
    3. Asserts that no `TypeError` or `Unexpected Argument` error is raised.
  </action>
  <verify>`pytest tests/test_interface_sync.py`</verify>
  <done>Tests pass for all three dataset types.</done>
</task>

## Success Criteria
- [ ] Dataset functions accept advanced tuning parameters.
- [ ] `pytest tests/test_interface_sync.py` passes.
- [ ] No more `TypeError` in GUI when running with high UMAP neighbors.
