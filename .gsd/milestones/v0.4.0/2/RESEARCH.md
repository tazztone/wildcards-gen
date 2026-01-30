---
phase: 2
level: 2
researched_at: 2026-01-30
---

# Phase 2 Research: Geometry-First Clustering

## Questions Investigated
1. Is `umap-learn` compatible with our current stack?
2. How should UMAP be integrated into the existing `linter`/`arranger` pipeline?
3. What are the appropriate hyperparameters for UMAP in this context?

## Findings

### Dependency Analysis
- `hdbscan` is already installed (v0.8.41).
- `umap-learn` is NOT installed.
- **Action**: Must add `umap-learn>=0.5.0` to `pyproject.toml` under `lint` extras.

### Pipeline Integration
Current flow in `arranger.py` (assumed future location):
`Embeddings (384d)` -> `HDBSCAN` -> `Cluster Labels`

Proposed flow:
`Embeddings (384d)` -> `UMAP (5d)` -> `HDBSCAN` -> `Cluster Labels`

**Why 5 dimensions?**
- HDBSCAN struggles with "curse of dimensionality" above ~10-15 dims.
- UMAP is excellent at preserving local neighborhood structure, which is what semantic clustering cares about.
- Reducing to 5 dims creates a dense "manifold" where density-based clustering works best.

### Configuration
Recommended defaults for typical wildcard list sizes (50-2000 items):
- **n_neighbors**: 15 (default value, good balance of local/global).
- **min_dist**: 0.0 or 0.1 (tighter packing for clustering).
- **n_components**: 5 (target dimension).
- **metric**: 'cosine' (best for semantic embeddings).

## Decisions Made
| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Manifold Learner** | **UMAP** | State-of-the-art for preserving structure; standard pair with HDBSCAN. |
| **Target Dim** | **5** | Low enough for HDBSCAN efficiency, high enough to keep info. |
| **Dependency** | **umap-learn** | Required addition. |

## Patterns to Follow
- **Optional Import**: Like `hdbscan`, `umap` should be imported inside the function or checked via `check_dependencies`.
- **Fallback**: If `umap` fails (e.g., too few samples), fallback to raw embeddings or PCA.

## Risks
- **Performance**: UMAP can be slow on very large datasets (>10k items).
    - *Mitigation*: Our leaf nodes are typically < 2000 items. Performance should be sub-second.

## Ready for Planning
- [x] Questions answered
- [x] Approach selected
- [x] Dependencies identified
