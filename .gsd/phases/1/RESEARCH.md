---
phase: 1
level: 2
researched_at: 2026-01-30
---

# Phase 1 Research: Stability Metrics

## Questions Investigated
1. What are the best metrics to measure taxonomy stability across runs?
2. How should the hierarchical YAML structure be represented for these metrics?
3. Are the necessary libraries available in the current stack?

## Findings

### Metric Selection
We need to measure two different aspects of stability:
1. **Content Stability**: Did the same terms appear in the output?
   - **Recommendation**: **Jaccard Index** on the set of unique terms.
2. **Structural Stability**: Did the terms group together in the same way?
   - **Recommendation**: **Adjusted Rand Index (ARI)**.
   - **Why**: ARI is robust to cluster naming. If `["dog", "cat"]` are in "Group 1" in run A, and in "Group Alpha" in run B, ARI is 1.0 (perfect match). This is critical for our semantic arranger which may fallback to non-deterministic names.

**Sources:**
- [scikit-learn Clustering Performance Evaluation](https://scikit-learn.org/stable/modules/clustering.html#clustering-performance-evaluation)

### Data Representation
To use ARI with a hierarchy, we must "flatten" the tree.
- **Approach**: Improve `StructureManager.extract_terms` to return `(term, path)` pairs.
- **Labeling**: The `path` string (e.g., `animal/mammal/canine`) serves as the "cluster label" for the term.
- **Handling Disjoint Sets**: ARI requires the same set of samples. We will compute ARI only on the **intersection** of terms between two runs. Terms present in one but not the other are penalized by the Content Stability metric (Jaccard).

### Dependencies
`scikit-learn` provides efficient implementations of `adjusted_rand_score` and `jaccard_score`.
- It is already defined in `pyproject.toml` under `optional-dependencies.lint`.
- The new `analytics` module should probably require this optional group or raise a friendly error.

## Decisions Made
| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Structural Metric** | **ARI** | Ignores cluster naming differences, focuses on grouping logic. |
| **Content Metric** | **Jaccard** | Standard measure for set similarity. |
| **Library** | **scikit-learn** | Standard, reliable, already in dependency tree. |
| **Flattening** | **Path strings** | Simple linear representation of hierarchy for clustering metrics. |

## Patterns to Follow
- **Graceful Failure**: If `scikit-learn` is missing, the `analyze` command should warn and exit, not crash the main app.
- **Immutable Inputs**: The comparator should not modify the input structures.

## Risks
- **Nested Structures**: "Soft" modifications (moving a sub-category up one level) might result in a drastic ARI drop if the path changes entirely.
    - *Mitigation*: This is acceptable. A path change *is* a structural change. We want to detect that.

## Ready for Planning
- [x] Questions answered
- [x] Approach selected
- [x] Dependencies identified
