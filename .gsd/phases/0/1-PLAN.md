---
phase: 0
plan: 1
wave: 1
---

# Plan 0.1: Tautology Pruning & Redundancy Filter

## Objective
Implement a new pass in `ConstraintShaper` that detects and collapses nodes where the parent name matches the child name (e.g., `Fish -> Fish -> [items]` becomes `Fish -> [items]`). This directly addresses the "Redundancy (Tautology)" issue identified in the Tencent YAML analysis.

## Context
- .gsd/SPEC.md
- .gsd/phases/0-quality-hardening/RESEARCH.md
- wildcards_gen/core/shaper.py

## Tasks

<task type="auto">
  <name>Implement _prune_tautologies method</name>
  <files>wildcards_gen/core/shaper.py</files>
  <action>
    Add a new method `_prune_tautologies(self, node: Any) -> Any` to the `ConstraintShaper` class.
    
    Logic:
    1. If `node` is not a dict, return as-is.
    2. Iterate through keys. For each key `parent_name`:
       - If the value is a dict with exactly 1 key `child_name`:
         - If `parent_name.lower().strip() == child_name.lower().strip()`:
           - Promote: Replace the parent's value with the grandchild content.
    3. Recurse on all dict values.
    
    Avoid:
    - Do NOT promote if the single child is a leaf list (that's intentional structure).
    - Do NOT use regex; simple string comparison is sufficient.
  </action>
  <verify>python -c "from wildcards_gen.core.shaper import ConstraintShaper; print('Import OK')"</verify>
  <done>Method exists and is callable without import errors.</done>
</task>

<task type="auto">
  <name>Wire tautology pass into shape()</name>
  <files>wildcards_gen/core/shaper.py</files>
  <action>
    Modify the `shape()` method to call `_prune_tautologies()` BEFORE `_flatten_singles()`.
    
    Order should be:
    1. _merge_orphans()
    2. _prune_tautologies()  # NEW
    3. _flatten_singles()
  </action>
  <verify>grep -n "_prune_tautologies" wildcards_gen/core/shaper.py</verify>
  <done>_prune_tautologies is called in the shape() method pipeline.</done>
</task>

<task type="auto">
  <name>Add unit test for tautology pruning</name>
  <files>tests/test_shaper.py</files>
  <action>
    Create or update `tests/test_shaper.py` with a test case:
    
    ```python
    def test_prune_tautologies():
        from wildcards_gen.core.shaper import ConstraintShaper
        
        # Input: Fish -> Fish -> [items]
        tree = {"Fish": {"Fish": ["salmon", "trout"]}}
        shaper = ConstraintShaper(tree)
        result = shaper.shape(min_leaf_size=0, flatten_singles=False)
        
        # Expected: Fish -> [items]
        assert result == {"Fish": ["salmon", "trout"]}
    ```
  </action>
  <verify>uv run pytest tests/test_shaper.py::test_prune_tautologies -v</verify>
  <done>Test passes.</done>
</task>

## Success Criteria
- [ ] `_prune_tautologies` method exists in `shaper.py`.
- [ ] `shape()` calls the new method in the correct order.
- [ ] Unit test for tautology pruning passes.
