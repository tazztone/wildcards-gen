# ROADMAP.md

> **Current Milestone**: v0.5.0 - Optimization & UI
> **Goal**: Polish the user experience and optimize performance now that the core engine is robust.

## Must-Haves
- [ ] **Async Generation**: Move long-running tasks to background threads to keep GUI responsive.
- [ ] **Compact Layout**: Optimizing `gui.py` use of vertical space (Collapsibles, Sidebar).
- [ ] **Live Preview**: "Preview" button in Builder tab to show first 50 lines of structure instantly.
- [ ] **Caching**: Aggressive caching for Synset lookups to speed up re-runs.

## Phases

### Phase 1: Async UI Foundation
**Status**: ⬜ Not Started
**Objective**: Refactor the centralized `cli.py`/`gui.py` invocation to support non-blocking execution (threaded/asyncio) and progress reporting.

### Phase 2: UI Refresh & Feature Exposure
**Status**: ⬜ Not Started
**Objective**: Reorganize the Gradio layout for compactness and expose all deep engine parameters (Smart/Arranger settings) to the user.


### Phase 3: Fast Preview Engine
**Status**: ⬜ Not Started
**Objective**: Implement a "Dry Run" pipeline that skips heavy clustering/shaping to just show the raw pruned structure instantly.

---
## Archived Milestones

### v0.4.0 - Data Science Core
- ✅ **Stability Metrics**: Implemented Jaccard/ARI.
- ✅ **Advanced Clustering**: UMAP+HDBSCAN.
- ✅ **Deterministic Naming**: Medoid/LCA naming.
- ✅ **Constraints Engine**: ConstraintsShaper.
- ✅ **Integration**: Full pipeline integration.

### v0.3.0 - UX Polish (Paused)
- [ ] Compact "Analysis" section.
- [ ] Move "Generation Completed" status.
