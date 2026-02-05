# Development Journal

## 2026-02-03: Phase 3 Stability Fixes
Fixed critical instability in the "Smart Arrangement" mode.

### Summary of Changes
1.  **Data Loss**: Isolated a logic error in `tencent.py` where nodes containing only semantically arranged orphans were being discarded by the flattening logic. Updated the "valid items" count to include arranged groups.
2.  **Budget**: Discovered that `preview_limit=0` was causing the traversal budget to exhaust immediately. Normalized this to `None` (unlimited).
3.  **Explosion/Duplication**: Suspected redundant item gathering. Added logic to rely on bubbled-up orphans rather than re-traversing sub-trees during flattening.
4.  **Parameter Propagation**: Found that `batch.py` was ignoring experimental thresholds for arrangement. Fixed the mapping to ensure tuning studies are effective.
5.  **Test Suite**: Updated and fixed 122 tests. Several tests were failing due to the new case-normalization logic (`ConstraintShaper`) which title-cases categories. Updated assertions to be case-insensitive or match the new standard.

### Outcome
Phase 3 is finalized. All core issues identified in the Tuning Study v1 (Data Loss and Multiplier effects) have been addressed and verified via synthetic tests and the full integration suite.

## 2026-02-05: Phase 5 - Hardening the Semantic Pipeline
Addressed architectural "weirdness" in semantic arrangement and structural pruning.

### Summary of Changes
1.  **Semantic Hallucination (Reactionary Fix)**: Discovered that `WordNet` prioritization was defaulting to frequency, leading to "Bourbon" (Person) -> "Reactionary". Updated `wordnet.py` to prioritize `noun.food`, `noun.animal`, etc.
2.  **Parent-Aware Naming**: Updated `Arranger` to prevent clusters from matching their parent's name. This eliminates `Beverage -> Beverage` tautologies.
3.  **Recursive Tautology Pruning**: Hardened `ConstraintShaper` to collapse deep redundant layers (e.g., `Dish -> Dish -> Dish`).
4.  **Conservative Flattening**: Refined flattening logic to preserve top-level semantic anchors (like `Matter`) while still pruning intermediate generic wrappers.
5.  **Comment Persistence**: Fixed a bug where YAML instructions were lost during dictionary transformations by explicitly copying the `ca` attribute in `ruamel.yaml`.
6.  **Labeling Quality**: Implemented TF-IDF coverage checks (>= 20%) and prefix filtering to prevent redundant labels like `Sauce (Sauce)`.

### Outcome
The generation framework is now context-aware. Large-scale outputs (Tencent ML-Images) show significantly improved readability and semantic coherence. "Reactionary" and double-nesting issues are resolved.
