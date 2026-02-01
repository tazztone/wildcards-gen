# Research: Phase 4 - Deep Parameter Collision

## Problem
The `TypeError: arrange_list() got multiple values for keyword argument 'return_metadata'` occurs because of a propagation pattern in the semantic engine:
1. `gui.py` calls `tencent.py` with `kwargs`.
2. `tencent.py` calls `smart.py:apply_semantic_arrangement` with `return_metadata=True`.
3. `smart.py` calls `arranger.py:arrange_hierarchy` and passes its own `return_metadata` flag INSIDE `kwargs`.
4. `arranger.py:arrange_hierarchy` calls `arrange_list` with a hardcoded `return_metadata=False` AND spreads the `kwargs`.

## Collision Analysis
In `arranger.py`:
```python
def arrange_hierarchy(terms, max_depth=2, ..., **kwargs):
    # ...
    groups, leftovers = arrange_list(terms, return_stats=False, return_metadata=False, **kwargs)
```
If `kwargs` contains `return_metadata`, this fails.

## Solution Strategy
1. **Sanitize `kwargs`**: Deep functions like `arrange_hierarchy` must "pop" control flags from `kwargs` before spreading them to downstream functions that have strict signatures for those same flags.
2. **Standardize Recursion**: Check if other parameters like `return_stats` have similar collisions.

## "Good Enough" Testing Strategy
The current signature tests only mock the top-level dataset function. They don't test the *propagation* to the semantic engine.

**New Integration Test (`tests/test_deep_integration.py`):**
- Use `unittest.mock` to intercept embedding calls (to keep it fast).
- Call `generate_dataset_handler` with real-world complex `kwargs` (Smart=True, semantic arrangement enabled).
- Allow the code to run through the dataset module -> smart.py -> arranger.py.
- This will catch the `TypeError` even if the embedding model isn't actually loaded.
