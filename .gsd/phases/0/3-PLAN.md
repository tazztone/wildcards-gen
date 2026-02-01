---
phase: 0
plan: 3
wave: 2
---

# Plan 0.3: Casing Normalization & Threshold Defaults

## Objective
Implement a unified casing strategy (Title Case categories, lowercase leaves) and update default thresholds to prevent semantic drift. This addresses the "Casing Inconsistency" and "Semantic Mismatch" issues from the analysis report.

## Context
- .gsd/SPEC.md
- .gsd/phases/0-quality-hardening/RESEARCH.md
- wildcards_gen/core/shaper.py
- wildcards_gen/core/presets.py

## Tasks

<task type="auto">
  <name>Implement _normalize_casing pass</name>
  <files>wildcards_gen/core/shaper.py</files>
  <action>
    Add a new method `_normalize_casing(self, node: Any) -> Any` to `ConstraintShaper`.
    
    Logic:
    1. If `node` is a list: return `[item.lower() for item in node]` (lowercase leaves).
    2. If `node` is a dict:
       a. Create a new dict.
       b. For each key, normalize to Title Case: `key.title()`.
       c. Recurse on values.
       d. Handle key collisions by merging lists.
    3. Return the normalized node.
    
    Wire into `shape()` as the LAST pass (after flatten_singles).
  </action>
  <verify>python -c "from wildcards_gen.core.shaper import ConstraintShaper; s = ConstraintShaper({'FOOD': ['Apple', 'BANANA']}); print(s.shape(min_leaf_size=0))"</verify>
  <done>Output shows `{'Food': ['apple', 'banana']}` (Title Case key, lowercase values).</done>
</task>

<task type="auto">
  <name>Update default thresholds in presets.py</name>
  <files>wildcards_gen/core/presets.py</files>
  <action>
    Update `SMART_PRESETS` to use stricter defaults:
    
    1. Change `semantic_arrangement_threshold` from implicit 0.1 to 0.3 in all presets.
    2. Lower `min_hyponyms` for "Balanced" from 50 to 30.
    3. Add a comment explaining the 0.3 threshold rationale.
    
    Note: The preset tuple format is `(min_depth, min_hyponyms, min_leaf, merge_orphans, semantic_clean, semantic_arrange, method)`.
    The threshold is NOT in this tuple—it's set in the GUI/CLI defaults.
    
    Action: Update the DEFAULT value in `cli.py` (`--semantic-arrange-threshold`) from 0.1 to 0.3.
  </action>
  <verify>grep -n "semantic-arrange-threshold" wildcards_gen/cli.py</verify>
  <done>Default threshold is 0.3 in CLI arg definition.</done>
</task>

<task type="auto">
  <name>Add unit test for casing normalization</name>
  <files>tests/test_shaper.py</files>
  <action>
    Add a test case for the casing normalization:
    
    ```python
    def test_normalize_casing():
        from wildcards_gen.core.shaper import ConstraintShaper
        
        tree = {"FOOD": {"fruit": ["Apple", "BANANA"]}}
        shaper = ConstraintShaper(tree)
        result = shaper.shape(min_leaf_size=0)
        
        # Keys should be Title Case, leaves lowercase
        assert "Food" in result
        assert "Fruit" in result["Food"]
        assert result["Food"]["Fruit"] == ["apple", "banana"]
    ```
  </action>
  <verify>uv run pytest tests/test_shaper.py::test_normalize_casing -v</verify>
  <done>Test passes.</done>
</task>

## Success Criteria
- [ ] `_normalize_casing` method exists and is called in `shape()`.
- [ ] Default `semantic-arrange-threshold` in CLI is 0.3.
- [ ] Unit test for casing normalization passes.
