---
phase: 3
level: 2
researched_at: 2026-01-30
---

# Phase 3 Research: Fast Preview Engine

## Goal
Sub-second response times in GUI when adjusting "Deep Tuning" sliders (UMAP/HDBSCAN), enabling real-time feedback.

## Current Bottlenecks

1.  **UMAP Reduction**:
    - `compute_umap_embeddings` runs every time.
    - Input: High-dim embeddings (e.g., 384-dim for 500-20k items).
    - Output: Low-dim embedding (5-dim).
    - Cost: Expensive for >1k items.
    - Status: **Uncached**.

2.  **HDBSCAN Clustering**:
    - Runs every time.
    - Cost: Moderate.
    - Status: **Uncached**.

3.  **Embeddings**:
    - `get_cached_embeddings` uses `_EMBEDDING_CACHE` (Global Dict).
    - Status: **Cached** (Good).

4.  **Tree Reconstruction**:
    - `generate_openimages_hierarchy` rebuilds tree structure from JSON every call.
    - Cost: Low (<0.1s for skeleton), but high if re-generating full list before clustering.

## Optimization Strategy

### 1. Cache UMAP Results
Since UMAP is deterministic (with `random_state=42`), we can cache the result keyed by:
- Input Embeddings Hash (SHA/MD5 of array buffer)
- `n_neighbors`
- `min_dist`
- `n_components`

**Implementation**:
- Add `_UMAP_CACHE` to `arranger.py`.
- Helper `hash_array(arr)` for numpy arrays.

### 2. Fast Path in GUI
- When `live_preview_handler` is triggered by *tuning sliders* (not dataset change), we should ideally skip tree reconstruction if possible.
- However, since `generate_dataset_handler` is stateless, it's hard to skip reconstruction without a persistent state object.
- **Compromise**: The tree build is fast. The *Arrangement* is slow. Caching UMAP/Clustering at the `arranger` level is sufficient.

## Plan
1.  **Implement `hash_array`** utility.
2.  **Add `_UMAP_CACHE`** in `arranger.py`.
3.  **Decorate/Wrap `compute_umap_embeddings`** to use cache.

## Risks
- Memory usage for cache.
- **Mitigation**: Use `LRUCache` with size limit (e.g. 10 most recent UMAPs).

## Verification
- Measure time for `arrange_list` on 2nd run with different HDBSCAN params (should skip UMAP).
