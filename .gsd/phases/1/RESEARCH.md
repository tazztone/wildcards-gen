# Research: Phase 1 - Signature Synchronization

## Problem
The GUI recently added advanced tuning sliders (UMAP Neighbors, Min Dist, HDBSCAN samples) which are passed via `smart_kwargs` to dataset generators. However, the `generate_*` functions in the dataset modules were not updated to accept these specific keyword arguments.

## Current vs Required Signatures

### Affected Functions
1. `wildcards_gen.core.datasets.imagenet.generate_imagenet_tree`
2. `wildcards_gen.core.datasets.tencent.generate_tencent_hierarchy`
3. `wildcards_gen.core.datasets.openimages.generate_openimages_hierarchy`

### Required New Parameters
- `umap_n_neighbors: int = 15`
- `umap_min_dist: float = 0.1`
- `hdbscan_min_samples: Optional[int] = None`

## Solution Strategy
1. Update all three functions to accept these keyword arguments.
2. Ensure they are passed into the `SmartConfig` constructor inside each function.
3. Validate that `coco.py` doesn't need changes (it currently doesn't support Smart mode, but we should verify it doesn't crash if called with extra kwargs).

## Testing Strategy
Create `tests/test_interface_sync.py`:
- Mock the underlying dataset logic to avoid long downloads.
- Call each generator with the exact dictionary of parameters provided by `gui.py`.
- Assert no `TypeError` is raised.
