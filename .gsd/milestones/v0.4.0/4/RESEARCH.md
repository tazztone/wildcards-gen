---
phase: 4
level: 2
researched_at: 2026-01-30
---

# Phase 4 Research: Constraints & Shaping

## Questions Investigated
1. **Orphans**: How to handle clusters smaller than `min_leaf_size`?
2. **Flattening**: When should a nested group be promoted to its parent?
3. **Implementation**: Inline (in `arrange_hierarchy`) vs Post-process?

## Findings

### 1. Handling Orphans (Min Size)
- **Problem**: HDBSCAN or recursion might produce tiny groups (e.g., "Group - 2 items").
- **Strategy**: **Merge to Sibling**.
    - If a group is < `min_size`, move its items to "Other" (or a generic "Misc" sibling).
    - If "Other" doesn't exist, create it.
    - If "Other" ends up being the *only* significant group, flatten the whole thing.

### 2. Flattening (User Preference)
- **Problem**: Deep nesting is annoying for simple usage.
- **Strategy**: `max_depth` (already in Phase 3) + **Promotion**.
    - If a node has a single child key (e.g., `Dog -> { Canine: [...] }`), promote `Canine` items to `Dog`.
    - If a cluster's score is low (weak quality) AND user wants "flat", dissolve it.

### 3. Implementation Strategy: Post-Processing
- Trying to handle strict constraints *during* recursive clustering is complex and messy.
- **Better Approach**: `ShapeManager` class.
    - Takes the raw nested dictionary from `arrange_hierarchy`.
    - Iterates (bottom-up?) to enforce constrains.
    - `prune_small_branches(tree, min_size=5)`
    - `flatten_singles(tree)`

## Decisions Made
| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Strategy** | **Post-Processing** | Separates "generating structure" (DS) from "polishing structure" (UX). |
| **Component** | **`ConstraintShaper`** | New class in `arranger.py` or `shaper.py`. `arranger.py` is fine for now. |
| **Action** | **Merge to 'Other'** | Safest way to handle orphans without deleting data. |

## Patterns to Follow
- **Functional**: The shaper should be pure transformations on the dict tree.
- **Configurable**: `min_leaf_size` should be passed down from CLI/GUI.

## Ready for Planning
- [x] Questions answered
- [x] Approach selected
