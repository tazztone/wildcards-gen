# ROADMAP.md

> **Current Milestone**: v0.8.0 - Stability & UI Polish
> **Goal**: Resolve regressions, harden tests, and streamline the CV generation interface.

## Must-Haves
- [ ] Fix `TypeError` in Dataset generation modules.
- [ ] Implement signature validation tests.
- [ ] Remove obsolete Analysis/History panels.
- [ ] Implement 2-column layout for CV Datasets tab.
- [ ] Improve Smart Tuning tooltips.

## Phases

### Phase 1: Stability & Validation
- **Objective**: Fix the immediate crash and prevent future interface regressions.
- **Tasks**:
    - Update ImageNet, Tencent, and Open Images generators to accept all Smart Tuning parameters.
    - Create `tests/test_signatures.py` to programmatically verify that dataset handlers and core functions are in sync.
- **Verification**: Tests passing; no more `TypeError` when tweaking UMAP/HDBSCAN settings in GUI.

### Phase 2: UI Structure
- **Objective**: Reorganize the interface for better ergonomics and space usage.
- **Tasks**:
    - Remove "Analysis Report" and "Run History" Accordions from `gui.py`.
    - Refactor "CV Datasets" tab internal layout to a 2-column format.
- **Verification**: Browser screenshot confirming cleaner layout and reclaimed space.

### Phase 3: UX Polish
- **Objective**: Improve the educational value of the settings.
- **Tasks**:
    - Add descriptive `info` strings to all Smart Tuning UI components in `gui.py`.
- **Verification**: All settings show helpful tooltips or inline text.

---
## Archived Milestones

### v0.7.0 - GUI Refactor
- ✅ **Logical Structure**: Organized `gui.py` into clear sections.
- ✅ **Verification**: Passed all GUI tests.