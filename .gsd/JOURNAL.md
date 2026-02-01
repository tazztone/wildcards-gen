# Project Journal

## 2026-01-30 - Phase 3 Completion: Fast Preview

### Summary
Successfully implemented the "Fast Preview" feature to allow rapid iteration on dataset generation settings. This involved a cross-functional update touching core logic (`smart.py`), all dataset generators (`tencent.py`, `imagenet.py`, `openimages.py`), and the frontend (`gui.py`).

### Key Decisions
- **Traversal Budget**: Implemented an inclusive budget mechanism in `smart.py`. This ensures we process *exactly* N items if possible, then stop.
- **Dataset Integration**: Each dataset generator now accepts an optional `preview_limit`. If set, it stops recursion early.
- **Bug Fix**: Discovered and fixed a logic error in `tencent.py` where empty/pruned nodes were causing the flattening fallback to grab ALL descendants, defeating the purpose of pruning.

### Refactor
- **GUI Hardening**: Following a Devil's Advocate review, I refactored `gui.py` to:
    - Make `preview_limit` configurable in `config.yaml`.
    - Fix fragile positional argument parsing in handlers.
    - Correct a variable scoping issue (`all_gen_inputs`) that caused a crash during initialization.

### Verification
- Created `tests/test_fast_preview.py` and `tests/test_gui_refactor.py` to verify budget constraints and event robustness.
- Verified that strict budget exhaustion leads to correct hierarchy truncation.
- Ran full regression suite: 23 tests passed (9 GUI, 14 Core).

### Next Steps
Proceeding to Phase 4 (Verification & Audit) for final sign-off.

---

## 2026-02-01 - Milestone v0.8.0 Initiation

### Summary
User identified the "ANALYSIS" panel (Analysis Report, Run History) as obsolete and requested its removal to reclaim UI space. 

### Key Decisions
- Captured the request as a high-priority entry for Milestone v0.8.0.
- Identified critical bug: `TypeError` in `tencent.py` due to missing `umap_n_neighbors` parameter.
- **Critical Requirement**: Hardened regression testing. The user emphasized that such interface mismatches must be caught by tests early to ensure zero runtime errors during execution.
- Added requirements for better documentation/tooltips in the UI.
- **UI Decision**: Rearrange the "📸 CV Datasets" tab into a cleaner 2-column layout while removing the obsolete Analysis panel.
- Planning Lock is in effect: `SPEC.md` and `ROADMAP.md` must be finalized before implementation.

### Status
- Milestone v0.8.0 executed.
- **CRITICAL BUG FOUND**: `TypeError: arrange_list() got multiple values for keyword argument 'return_metadata'`.
- User Feedback: "your tests aren't good enough".
- Action: Added **Phase 4: Deep Stability & Integration Testing** to the roadmap.
- Next: `/plan 4`.

---

## 2026-02-01 - Milestone v0.8.0 Completion & Archival

### Summary
Milestone v0.8.0 ("Stability & UI Polish") has been successfully completed and archived. This milestone was critical for addressing deep-stack `TypeError` regressions and modernizing the UI/UX.

### Key Decisions
- **AST-Based Registry Guard**: Implemented `tests/test_gui_registry.py`. Instead of manual checks, this uses Python's `ast` module to scan `gui.py` and ensure every configuration input has an `info=` tooltip. This satisfies the "content preservation" requirement and prevents future "silent" UX regressions.
- **2-Column UI Layout**: Successfully transitioned the CV Datasets tab to a sidebar-configuration model. This significantly reduced vertical scrolling and reclaimed space from the obsolete Analysis panel.
- **Deep Integration Testing**: Added `tests/test_deep_integration.py` which simulates full generation cycles with advanced smart tuning enabled, catching signature mismatches that unit tests missed.

### Verification
- All 115 tests passed.
- Verified fix for Tencent `umap_n_neighbors` parameter.
- Verified synchronization of `test_ui_wiring.py` (29 parameters) and `test_ui_logic.py` (6 returns).

### Next Steps
Moving to **Milestone v0.9.0: Performance & Expansion**. Focus will be on parallelizing the embedding generation in the Arranger and expanding export capabilities to JSONL.
