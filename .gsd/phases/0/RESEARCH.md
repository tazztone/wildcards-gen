---
phase: 0
level: 2
researched_at: 2026-02-01
---

# Phase 0 Research: Quality Hardening (The "Gold Standard" Initiative)

## Questions Investigated
1. **Redundancy Filter**: How to detect and prune `Fish -> Fish` tautologies?
2. **Descriptive "Other"**: How to replace generic labels with TF-IDF context?
3. **Unified Casing**: How to enforce Title Case categories and lowercase leaves?
4. **Semantic Strictness**: Impact of the 0.3 threshold.

## Findings

### 1. Pruning Tautologies (Redundancy Filter)
- **Current State**: `shaper.py` has `_flatten_singles` which promotes content but doesn't check for name identity.
- **Solution**: Add a `TautologyPass` to `ConstraintShaper`. 
- **Logic**: If `parent_name.lower() == child_name.lower()`, move child contents to parent and delete child. This is particularly frequent in Tencent and ImageNet.

### 2. Descriptive "Other" Blocks
- **Current State**: Small groups are merged into a generic "Other" list.
- **Improved Approach**: Use the `extract_unique_keywords` functionality from `arranger.py`. 
- **Logic**: When merging $N$ terms into "Other", compute their top TF-IDF keyword relative to the rest of the file. Rename "Other" to "Other (Keyword)".
- **Integration**: `arranger.py` should export `generate_contextual_label(terms, context)` for use by the `Shaper`.

### 3. Casing Normalization
- **Requirement**: "Title Case" for categories, "lowercase" for leaf items.
- **Risk**: WordNet synsets and dataset lookups are case-sensitive or rely on standard lemmas.
- **Safe Implementation**: Perform casing normalization in the `Dataset.generate_...` function's final return pass, or as a standalone `Shaper` pass. 

### 4. Traversal Budget & thresholds
- **Finding**: The 500-node limit is too aggressive for production runs. 
- **Thresholds**: The report is correct—0.1 is too liberal. It allows semantic "drift" (tacos in soup). 0.3 is the mathematical "sweet spot" for MiniLM embeddings to ensure high similarity.

## Decisions Made
| Decision | Choice | Rationale |
|----------|--------|-----------|
| Tautology Logic | Name-based promotion | Simple, effective, handles dataset-induced redundancy. |
| Other Labels | TF-IDF (1 keyword) | Adds context without adding too much visual noise. |
| Casing Timing | Post-Generation Pass | Minimizes side-effects during recursive traversal. |
| Default `min_hyponyms` | 50-200 | 1000 was effectively disabling mid-level categories. |

## Patterns to Follow
- **Pass-based Shaping**: Implement each refinement as a discrete method in `ConstraintShaper` to keep code clean.
- **Case-Insensitive Comparison**: Always `.lower().strip()` before comparing node names for tautology detection.

## Anti-Patterns to Avoid
- **Greedy Flattening**: Don't flatten if the single child is a leaf list (preserves classification context).
- **Over-Categorization**: Don't create "Other (Keyword)" if the keyword score is very low; stick to plain "Other".

## Ready for Planning
- [x] Redundancy logic mapped
- [x] Casing strategy defined
- [x] Budget lift strategy confirmed
