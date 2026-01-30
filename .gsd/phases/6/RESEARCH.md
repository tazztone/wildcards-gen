# Research - Phase 6: Service Restoration

## Context
Phase 5 (Regression Repair) addressed critical functional regressions but left the test suite in a fractured state. The full suite run revealed 10+ failures due to drift between the implementation (which evolved in Phase 1-4) and the tests (which use stale mocks or expectations).

## Failure Analysis

### 1. Arranger Tests (`test_arranger.py`, `test_arranger_umap.py`)
- **Issue**: `AssertionError: 'fruit' not found`.
- **Cause**: The `apply_semantic_arrangement` logic now uses UMAP/HDBSCAN by default or expects specific config. The tests likely use simple list logic that is now wrapped or modified.
- **Issue**: `test_arrange_single_pass_calls_umap` calls 0 times.
- **Cause**: The `compute_umap_embeddings` is likely cached (lru_cache) or validly skipped, but the test mock expects a call.
- **Fix**: Clear UMAP cache in tests (`arranger._UMAP_CACHE.clear()`) and update mocks to match new signatures.

### 2. Dataset Fixes (`test_dataset_fixes.py`)
- **Issue**: `AttributeError: 'str' object has no attribute 'items'`.
- **Cause**: The test mocks `load_openimages_data` or `apply_semantic_arrangement` to return a plain dictionary, but the recursive logic in `openimages.py` (updated in Phase 5) now expects specific tuple unpacking or handles recursion differently.
- **Fix**: Update mocks to return `(structure, leftovers, metadata)` tuples where required.

### 3. Shaper Tests (`test_shaper.py`)
- **Issue**: `AssertionError: assert 'Level3' in ['items']`.
- **Cause**: The test expects flattening behavior, but `shaper.py` logic for `flatten_singles` might be more conservative or the test setup (single item list) triggers the "don't flatten leaf container" rule differently.
- **Fix**: Adjust `test_shaper.py` expectations or explicit config (`preserve_roots=False`).

### 4. Fast Preview (`test_fast_preview.py`)
- **Issue**: `TypeError: '<' not supported between instances of 'MagicMock'`.
- **Cause**: Sorting logic in `tencent.py` or `amenities` uses `str.casefold`. Mocks are returning MagicMocks for names/ids, which fail comparison.
- **Fix**: Configure `MagicMock` names to return actual strings.

## Strategy
Update the test suite to reflect reality. Do not revert functional code changes unless they are incorrect. Trust the Phase 5 logic fixes (verified by smoke tests) and align the unit tests.
