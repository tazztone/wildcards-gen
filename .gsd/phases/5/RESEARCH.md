---
phase: 5
level: 2
researched_at: 2026-02-05
---

# Phase 5: Architectural Improvements (Research)

## Questions Investigated
1. **Why does the hierarchy start with "Matter"?** (Hallucinated/Unwanted Root)
2. **Why is the nesting so deep?** (e.g., `Food -> Beverage -> Alcohol -> Wine`)
3. **How to fix redundant siblings?** (e.g., `Sauce (Bearnaise)` next to `General Sauce`)

## Findings

### 1. The "Matter" Root (Validated / Inconsistent)
The user confirmed that "Matter" is a VALID root for physical taxonomies.
- **Current Issue**: `arranger.py` blocks it in `get_lca_name` (blacklist) but allows it in `get_medoid_name` (fallback).
- **Result**: The code produces "Matter" only by accident (fallback).
- **Goal**: Make "Matter" explicitly allowed by centralizing the blacklist and removing it from the banned set.

**Recommendation:**
- Centralize `BLACKLIST_CATEGORIES` in `config.py`.
- Ensure "Matter" / "Physical Entity" are **NOT** in the blacklist if the user wants them.
- Apply the same blacklist to both LCA and Medoid for consistency.

### 2. Deep Nesting (`shaper.py` Correctness)
The hierarchy `Food -> Beverage -> Alcohol -> Wine` was flagged as too deep, but the user confirmed it is logically precise and desirable.
- **Current Logic**: `shaper.py` preserves single-child dicts. This is now confirmed as **Correct Behavior**.
- **Issue**: There is no issue here to fix, but we should ensure this behavior is preserved by regression tests.

### 3. Tautology Handling (Ambiguous)
`Sauce (Bearnaise)` next to `General Sauce` is a result of Hybrid Naming + Leftover management.
- `Sauce (Bearnaise)` is a valid cluster (centered on Bearnaise).
- `General Sauce` is the leftovers.
- This structure is acceptable for now given the preference for depth/precision.

## Decisions Made
| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Blacklist Strategy** | **Centralized Config** | Move harcoded sets to `config.py`. Explicitly Allow "Matter". |
| **Flattening Strategy** | **Preserve Deep Paths** | Keep `_flatten_singles` conservative logic as it produces the desired precision. |

## Risks
- **None**: We are essentially codifying the current behavior as spec.

## Ready for Planning
- [x] Questions answered
- [x] Approach selected
