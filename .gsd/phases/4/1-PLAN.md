---
phase: 4
plan: 1
wave: 1
---

# Plan 4.1: Deep Stability & Integration Testing

## Objective
Normalize parameter propagation in the semantic engine to prevent `TypeError` collisions and implement end-to-end integration tests that validate the entire generation stack.

## Context
- `.gsd/SPEC.md`
- `.gsd/phases/4/RESEARCH.md`
- `wildcards_gen/core/arranger.py`
- `wildcards_gen/core/smart.py`
- `wildcards_gen/gui.py`

## Tasks

<task type="auto">
  <name>Sanitize Parameter Propagation</name>
  <files>
    - /home/tazztone/_coding/wildcards-gen/wildcards_gen/core/arranger.py
    - /home/tazztone/_coding/wildcards-gen/wildcards_gen/core/smart.py
  </files>
  <action>
    Fix the `multiple values for keyword argument` collision:
    1. In `arranger.py:arrange_hierarchy`, pop `return_metadata` and `return_stats` from `kwargs` before calling `arrange_list`.
    2. Audit `smart.py` to ensure it doesn't pass downstream control flags inside `kwargs`.
  </action>
  <verify>Check `arrange_hierarchy` code for `.pop()` calls on collision-prone arguments.</verify>
  <done>Code handles residual `kwargs` safely without hitting duplicate argument errors.</done>
</task>

<task type="auto">
  <name>Implement Deep Integration Test</name>
  <files>
    - /home/tazztone/_coding/wildcards-gen/tests/test_deep_integration.py
  </files>
  <action>
    Create a robust integration test that:
    1. Mocks `sentence_transformers` and `umap`/`hdbscan` to bypass heavy compute.
    2. Calls `gui.generate_dataset_handler` for each dataset (ImageNet, Tencent, OpenImages) with "Smart" mode and "Semantic Arrangement" ENABLED.
    3. Verifies that the execution completes without ANY `TypeError` or stack-level crashes.
    4. Ensures that advanced tuning params (umap_n_neighbors, etc.) actually reach the `arrange_list` function.
  </action>
  <verify>`uv run pytest tests/test_deep_integration.py`</verify>
  <done>Tests pass for the full stack under high-stress parameter configurations.</done>
</task>

## Success Criteria
- [ ] No duplicate argument collisions in the arranger stack.
- [ ] Comprehensive integration test validates the full GUI -> Dataset -> Smart -> Arranger chain.
- [ ] `pytest` coverage for the specific crash reported by the user.
