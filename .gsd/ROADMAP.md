# ROADMAP.md

> **Current Milestone**: v0.9.0 - Performance & Expansion [IN PROGRESS]
> **Goal**: Scale generation capabilities through batch processing and improved throughput.

## Must-Haves
- [ ] Implement CLI batch mode for processing multiple roots/datasets.
- [ ] Add JSONL export support for machine-learning ingest compatibility.
- [ ] Create customizable instruction templates for LLM enrichment.
- [ ] Parallelize embedding generation in `Arranger` for 2x faster clustering.

## Phases

### Phase 0: Quality Hardening (The "Gold Standard")
**Status**: ✅ Completed
**Objective**: Address qualitative regressions identified in the Tencent run (naming, casing, redundancy).

### Phase 1: Throughput & Scaling
**Status**: 🏃 In Progress
**Objective**: Optimize the Arranger for multi-core processing and implement batch CLI commands.

### Phase 2: Interoperability
**Status**: ⏳ Planned
**Objective**: Expand export formats and implement template-based instruction generation.

---

## Archived Milestones

### v0.8.0 - Stability & UI Polish
- ✅ **Stability**: Fixed signature mismatch regressions and Tencent `TypeError`.
- ✅ **Test Coverage**: Added `tests/test_interface_sync.py` and `tests/test_deep_integration.py`.
- ✅ **UI Design**: Implemented 2-column CV Layout and removed obsolete analysis sections.
- ✅ **Registry Guard**: Implemented AST-based tooltip validation in `tests/test_gui_registry.py`.

### v0.7.0 - GUI Refactor
- ✅ **Logical Structure**: Organized `gui.py` into clear sections.
- ✅ **Verification**: Passed all GUI tests.

### v0.6.0 - Smart Arrangement (Gap Closure)
- ✅ **Arranger**: Implemented semantic clustering with UMAP/HDBSCAN.
- ✅ **Integration**: Wired Arranger into ImageNet/OpenImages pipelines.