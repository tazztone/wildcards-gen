# ROADMAP.md

> **Current Milestone**: v0.8.0 - Stability & UI Polish [COMPLETE]
> **Goal**: Resolve regressions, harden tests, and streamline the CV generation interface.

## Must-Haves
- [x] Fix `TypeError` in Dataset generation modules.
- [x] Implement signature validation tests.
- [x] Remove obsolete Analysis/History panels.
- [x] Implement 2-column layout for CV Datasets tab.
- [x] Improve Smart Tuning tooltips.

## Phases

### Phase 1: Stability & Validation
**Status**: ✅ Complete

### Phase 2: UI Structure
**Status**: ✅ Complete

### Phase 3: UX Polish
**Status**: ✅ Complete

### Phase 4: Deep Stability & Integration Testing
**Status**: ✅ Complete
**Objective**: Resolve deep-stack `TypeError` regressions in the semantic arrangement logic and implement multi-layer integration tests to ensure zero-runtime errors.
**Depends on**: Phase 3

**Tasks**:
- [ ] Fix `arrange_list` / `arrange_hierarchy` parameter collision.
- [ ] Implement `tests/test_deep_integration.py` that simulates full generation with advanced tuning.

**Verification**:
- `pytest tests/test_deep_integration.py` passing with all Smart Tuning features enabled.

### Phase 5: Quality Assurance & Registry
**Status**: ✅ Complete
**Objective**: Fix regressions in legacy UI tests, synchronize parameter wiring, and implement registry-based validation for tooltips and presets.
**Depends on**: Phase 4

**Tasks**:
- [ ] Fix `test_ui_logic.py` return count.
- [ ] Synchronize `test_ui_wiring.py` with modern 30-parameter signature.
- [ ] Implement `tests/test_gui_registry.py` for Tooltips and Smart Presets.

**Verification**:
- All 35+ test suites passing with zero failures.
- `test_gui_registry.py` confirms 100% tooltip coverage.

---
## Archived Milestones

### v0.8.0 - Stability & UI Polish
- ✅ **Stability**: Fixed signature mismatch regressions.
- ✅ **Test Coverage**: Added `tests/test_interface_sync.py` to target parameter mismatches.
- ✅ **UI Design**: Implemented 2-column CV Layout and removed obsolete analysis sections.
- ✅ **UX Guidance**: Added comprehensive info tooltips to all smart tuning settings.

### v0.7.0 - GUI Refactor
- ✅ **Logical Structure**: Organized `gui.py` into clear sections.
- ✅ **Verification**: Passed all GUI tests.