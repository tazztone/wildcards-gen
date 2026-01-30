# ROADMAP.md

> **Current Milestone**: v0.4.0 - Data Science Core
> **Goal**: Upgrade the taxonomy generation engine with strict data science methodologies (stability metrics, geometry-first clustering, deterministic naming) to produce high-quality, reproducible, and human-editable YAML artifacts.

## Must-Haves
- [ ] **Stability Metrics**: Measurable "diff stability" (Jaccard/Edit Distance) between runs.
- [ ] **Advanced Clustering**: UMAP → HDBSCAN pipeline for better separation in high-cardinality leaves.
- [ ] **Deterministic Naming**: Keyphrase extraction (TF-IDF/KeyBERT) to replace "Group N".
- [ ] **Hierarchical Leaves**: Recursive clustering for multi-level sub-categorization.
- [ ] **Constraints Engine**: Rule-based override system (must-link/cannot-link) for taxonomy shaping.

## Phases

### Phase 1: Stability & Metrics Foundation
**Status**: ✅ Complete
**Objective**: Implement the "Yardstick". Build the analysis tools to measure taxonomy stability and quality (cluster validity indices). We cannot improve what we cannot measure.
**Tasks**:
- [x] Create `wildcards_gen/analytics/metrics.py` for stability calculations (Jaccard, etc.).
- [x] Implement `ClusterReport` class to track validity indices (Silhouette, DBCV).
- [x] Add CLI command `analyze-stability` to compare two YAML files.

### Phase 2: Geometry-First Clustering
**Status**: ✅ Complete
**Objective**: Implement the UMAP dimensionality reduction pipeline feeding into HDBSCAN, allowing for "blobby" cluster detection and better outlier rejection in dense semantic spaces.

### Phase 3: Recursive Hierarchy & Formatting
**Status**: ✅ Complete
**Objective**: Implement recursive sub-clustering for large leaves and strict deterministic naming (Keyphrase extraction) to eliminate "Group N".

### Phase 4: Constraints & Shaping
**Status**: ✅ Complete
**Objective**: Build the "Editor" layer—a rule engine that respects user-defined overrides (merges, splits, bans) to post-process the generated probability map.

### Phase 5: Integration
**Status**: ✅ Complete
**Objective**: Integrate Data Science components into the main generation pipeline.

### Phase 6: Gap Closure (Integration Fixes)
**Status**: ⬜ Not Started
**Objective**: Fix regressions in OpenImages/Tencent datasets and fully propagate ConstraintShaper logic.

**Gaps to Close:**
- [ ] Fix `openimages.py` API break (nested result handling).
- [ ] Fix `tencent.py` API break (assumed).
- [ ] Integrate `ConstraintShaper` into `openimages.py`.
- [ ] Integrate `ConstraintShaper` into `tencent.py`.

---
## Archived Milestones

### v0.3.0 - UX Polish (Paused)
- [ ] Compact "Analysis" section to save vertical space.
- [ ] Move "Generation Completed" status to a fixed/prominent place.
