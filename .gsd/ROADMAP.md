# ROADMAP.md

> **Current Phase**: Phase 4: Verification & Audit
> **Milestone**: v0.2.0 (Stabilization)

## Must-Haves (from SPEC)
- [x] 100% Green Test Suite
- [x] Consolidated `pyproject.toml`
- [x] Fast Preview Mode in GUI/Core

## Phases

### Phase 1: Bug Squashing (Regressions)
**Status**: ✅ Done
**Objective**: Fix the 5 critical test failures identified during mapping.
**Tasks**:
- [x] Fix `ValueError` in `tencent.py` (unpacking 3 vs 2 from `apply_semantic_arrangement`)
- [x] Fix `TypeError` in `test_config_integrity.py` (str vs int comparison)
- [x] Resolve `AssertionError` in `test_datasets.py` (ImageNet/OpenImages tree validation)
- [x] Verify fix with `uv run pytest`

### Phase 2: Dependency Unification
**Status**: ✅ Done
**Objective**: Modernize the package structure.
**Tasks**:
- [x] Move `gradio` and other missing libs to `pyproject.toml`
- [x] Update optional dependencies groups
- [x] Remove `requirements.txt`
- [x] Update install/run scripts to use `pip install -e .`

### Phase 3: Fast Preview Implementation
**Status**: ✅ Done
**Objective**: Improve the feedback loop for setting tuning.
**Tasks**:
- [x] Update dataset generator base/core to support `limit_items` parameter
- [x] Plumb `preview` flag through the CLI
- [x] Add "Preview Mode (First 500 items)" checkbox to Gradio GUI
- [x] Ensure instantaneous preview generation for huge datasets

### Phase 4: Verification & Audit
**Status**: 🚧 In Progress
**Objective**: Ensure the system is robust for handoff.
**Tasks**:
- [ ] Full regression test suite run
- [ ] Manual GUI verification of preview mode
- [ ] Final state dump and journal entry
