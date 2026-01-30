---
phase: 3
level: 2
researched_at: 2026-01-30
---

# Phase 3 Research: Recursive Hierarchy & Formatting

## Questions Investigated
1. How to handle "Group N" fallback naming deterministically?
2. How to split large clusters recursively?
3. Should we use an external library (KeyBERT) or simple TF-IDF?

## Findings

### Deterministic Naming
- **Problem**: When WordNet (LCA/Hypernym) fails, we fallback to "Group 1", "Group 2". This is unstable (indexes change) and uninformative.
- **Solution**: **TF-IDF Keyword Extraction**.
    - Treat the cluster as a "document" and the rest of the terms as "corpus".
    - Extract top 1-2 unique tokens.
    - Example: `["golden retriever", "labrador retriever"]` -> **"Retriever"**.
- **Libraries**: `scikit-learn` (already installed) is sufficient. `KeyBERT` is heavy (requires BERT model) and likely overkill for short phrases.

### Recursive Clustering
- **Current**: 2-pass system (Main + Leftovers).
- **Proposed**: `arrange_hierarchy(terms, depth=0)`
    - Base case: `len(terms) < min_size` or `depth > max_depth`.
    - Recursion: After clustering, if a cluster size > `max_leaf_size` (e.g., 50), call `arrange_hierarchy` on that cluster's items.
    - Nesting: The YAML structure naturally supports this. `arranger` needs to return a nested dict structure, not just a flat group map.

### Formatting
- The current `StructureManager` handles comment preservation well.
- New requirement: Ensure "Instruction" comments can be generated for sub-groups if needed? (Probably out of scope for auto-generation, but good to keep in mind).

## Decisions Made
| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Naming Fallback** | **TF-IDF** | Deterministic, informative, zero extra weight (using sklearn). |
| **Structure** | **Recursive** | Allows handling 1000+ item lists by breaking them down into manageable chunks of ~50. |
| **Max Depth** | **3** | Prevent infinite loops or unusable deep nesting. |

## Patterns to Follow
- **Safety**: Always have a depth limit for recursion.
- **Stability**: Sort terms before processing to ensure deterministic TF-IDF scores.

## Ready for Planning
- [x] Questions answered
- [x] Approach selected
- [x] Dependencies identified
