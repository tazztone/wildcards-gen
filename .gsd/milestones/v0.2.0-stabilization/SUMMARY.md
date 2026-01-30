# Milestone: v0.2.0-stabilization

## Completed: 2026-01-30

## Deliverables
- ✅ **100% Green Test Suite**: Fixed critical regressions in `tencent.py`, `config.py`, and `test_datasets.py`.
- ✅ **Consolidated Dependency Management**: Switched to `uv` and `pyproject.toml` as single source of truth.
- ✅ **Fast Preview Mode**: Implemented traversal budgets in core and live-preview debouncing in GUI.
- ✅ **GUI Hardening**: Refactored event handlers and made preview limits configurable.

## Phases Completed
1. **Phase 1: Bug Squashing** — 2026-01-30
2. **Phase 2: Dependency Unification** — 2026-01-30
3. **Phase 3: Fast Preview Implementation** — 2026-01-30
4. **Phase 4: Verification & Audit** — 2026-01-30

## Metrics
- **Total Commits**: 4 during stabilization phase.
- **Verification PASS**: 23/23 tests green.
- **Feature Performance**: ImageNet preview time reduced from >10s to <100ms.

## Lessons Learned
- **Recursion vs Budgets**: In large taxonomies, simple depth limits aren't enough; item-count budgets are essential for stable performance.
- **Gradio Event Handling**: Programmatic updates can trigger event storms; debouncing at the UI layer is a vital safety net.
- **WordNet Mapping**: Tencent and ImageNet share WNID schemas, but NLTK WordNet pos/offset handling requires strict verification to avoid indexing errors.
