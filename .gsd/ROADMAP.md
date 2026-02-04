# ROADMAP.md

> **Current Milestone**: v1.0.0 - Production Readiness [PLANNED]
> **Goal**: Final stabilization, performance tuning, and comprehensive documentation for public release.

## Must-Haves
- [ ] Final performance audit for large-scale datasets (1M+ items).
- [ ] Implement user-friendly installation wizard for Windows/Linux.
- [ ] Complete API documentation for `wildcards_gen` core.

## Phases

### Phase 4: Final Verification & Cleanup
**Status**: 📋 Planned
**Objective**: Final integration testing across all datasets and platforms.

---

## Archived Milestones

### v0.9.0 - Performance & Expansion
- ✅ **Batch Processing**: Implemented CLI batch mode for processing multiple roots/datasets.
- ✅ **Interoperability**: Added JSONL export support for ML ingest.
- ✅ **Customization**: Created customizable instruction templates for LLM enrichment.
- ✅ **Parallelism**: Parallelized embedding generation via job-level concurrency in `BatchProcessor`.
- ✅ **Stability**: Resolved critical data loss and duplication loops in Smart Arrangement (Phase 3).

### Phase 0: Quality Hardening (The "Gold Standard")
- ✅ **Status**: Completed
- ✅ **Objective**: Address qualitative regressions identified in the Tencent run (naming, casing, redundancy).

### Phase 1: Throughput & Scaling
- ✅ **Status**: Completed
- ✅ **Objective**: Optimize the Arranger for multi-core processing and implement batch CLI commands.

### Phase 2: Interoperability
- ✅ **Status**: Completed
- ✅ **Objective**: Expand export formats and implement template-based instruction generation.

### Phase 3: Smart Arrangement Stability
- ✅ **Status**: Completed
- ✅ **Objective**: Diagnose and fix critical instability in the Arranger (duplication loops and data loss).

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
