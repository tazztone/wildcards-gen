---
phase: 0
plan: 2
wave: 1
---

# Plan 0.2: Descriptive "Other" Labels via TF-IDF

## Objective
Replace generic "Other" labels with contextual ones (e.g., `Other (Alcoholic)`) by leveraging the existing TF-IDF keyword extraction logic in `arranger.py`. This addresses the "Generic Fallbacks" issue from the analysis report.

## Context
- .gsd/SPEC.md
- .gsd/phases/0-quality-hardening/RESEARCH.md
- wildcards_gen/core/arranger.py
- wildcards_gen/core/shaper.py

## Tasks

<task type="auto">
  <name>Export generate_contextual_label from arranger</name>
  <files>wildcards_gen/core/arranger.py</files>
  <action>
    Create a new public function `generate_contextual_label(terms: List[str], context_terms: List[str], fallback: str = "Other") -> str`.
    
    Logic:
    1. Call `extract_unique_keywords(terms, context_terms, top_n=1)`.
    2. If a keyword is found with score > 0.15, return `f"{fallback} ({keyword.title()})"`.
    3. Otherwise, return `fallback`.
    
    This wraps the existing internal TF-IDF logic for external use.
  </action>
  <verify>python -c "from wildcards_gen.core.arranger import generate_contextual_label; print(generate_contextual_label(['beer', 'wine'], ['apple', 'banana']))"</verify>
  <done>Function is importable and returns a string like "Other (Beer)" or "Other".</done>
</task>

<task type="auto">
  <name>Use contextual labels in _merge_orphans</name>
  <files>wildcards_gen/core/shaper.py</files>
  <action>
    Modify `_merge_orphans()` to use `generate_contextual_label` when creating "Other" buckets.
    
    Steps:
    1. Import `generate_contextual_label` from `wildcards_gen.core.arranger` (guard with try/except for missing deps).
    2. After collecting `small_keys` items, compute context as all other terms in `processed_node`.
    3. Call `generate_contextual_label(orphan_items, context_items)` to get the label.
    4. Use this label instead of hardcoded "Other".
    
    Avoid:
    - If import fails (missing sentence-transformers), fall back to plain "Other".
  </action>
  <verify>grep -n "generate_contextual_label" wildcards_gen/core/shaper.py</verify>
  <done>Contextual label function is called in _merge_orphans.</done>
</task>

## Success Criteria
- [ ] `generate_contextual_label` is exported from `arranger.py`.
- [ ] `_merge_orphans` uses the new function to name "Other" blocks.
- [ ] Graceful fallback if dependencies are missing.
