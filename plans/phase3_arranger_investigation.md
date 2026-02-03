# Phase 3: Smart Arrangement Investigation Plan

## Context
The "Tuning Study v1" identified critical failures in the `arrange=True` (Smart Arrangement) mode:
1.  **Explosion**: `leaf_size=10` resulted in 4x data duplication (9046 items vs ~2277).
2.  **Data Loss**: `leaf_size=30` and `50` resulted in >90% data loss.
3.  **Ineffective Threshold**: Changing `threshold` from 0.1 to 0.2 had no effect.

## Objectives
1.  Isolate the root cause of the **duplication loop** at small leaf sizes.
2.  Determine why items are **discarded** at large leaf sizes.
3.  Verify if the `threshold` parameter is correctly propagated to the clustering algorithm.

## Hypotheses

### H1: Recursion/Duplication Loop (`leaf_size=10`)
**Theory**: The `Arranger` logic might be re-processing existing categories or failing to mark items as "placed," leading to infinite or repeated insertion until a depth limit or memory limit is hit.
**Test**:
- Run a minimal reproduction script with `leaf_size=10` on a small subset of the Tencent dataset.
- Add logging to the placement/recursion function in `wildcards_gen/core/arranger.py`.

### H2: Strict Clustering Discards Outliers (`leaf_size=30+`)
**Theory**: When the target cluster size is large (e.g., 30 or 50), the clustering algorithm (HDBSCAN/UMAP) or the post-processing logic might be discarding items that don't fit into these large clusters, instead of falling back to a "Misc" bucket.
**Test**:
- Run a minimal reproduction with `leaf_size=50`.
- Inspect the "Unclustered" or "Noise" handling logic in the `Arranger`.

### H3: Threshold Propagation
**Theory**: The `threshold` parameter is not being passed correctly to the `StructureManager` or `Arranger` instance from the CLI/Batch runner.
**Test**:
- Inspect `wildcards_gen/batch.py` and `wildcards_gen/core/structure.py` to trace the variable.
- Add print debugging to verify the value at the point of usage.

## Plan of Action

### Step 1: Reproduction & Tracing
- Create `debug_arrangement.py` (or update existing) to run a single configuration:
    - `arrange=True`, `leaf_size=10` (expect explosion)
    - `arrange=True`, `leaf_size=50` (expect loss)
- **Action**: detailed logging of input count vs. output count.

### Step 2: Code Review & Fix
- Audit `wildcards_gen/core/arranger.py` (or equivalent location for clustering logic).
- Look for:
    - Recursion termination conditions.
    - Handling of HDBSCAN `-1` (noise) labels.
    - Usage of `threshold` parameter.

### Step 3: Verification
- Re-run the problematic configurations from Tuning Study v1.
- Expect:
    - `leaf_size=10`: Count remains ~2277 (no explosion).
    - `leaf_size=50`: Count remains ~2277 (no loss, higher orphan/misc count).
    - `threshold`: Distinct results for 0.1 vs 0.2.
