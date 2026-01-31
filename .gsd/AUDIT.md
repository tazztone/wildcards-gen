# Milestone Audit: v0.5.0 - Optimization & UI

**Audited:** 2026-01-31

## Summary
| Metric | Value |
|--------|-------|
| Phases | 6 |
| Gap closures | 3 (Phases 4, 5, 6) |
| Technical debt items | 2 (Integration test instability, strict mocks) |

## Must-Haves Status
| Requirement | Verified | Evidence |
|-------------|----------|----------|
| **Async Generation** | ✅ | `gui.py` uses Gradio event handlers with progress callbacks; non-blocking execution. |
| **Compact Layout** | ✅ | Implemented via Sidebar, Accordions (Deep Tuning), and 2-column layout in `gui.py`. |
| **Live Preview** | ✅ | `save_and_preview` logic in `gui.py` (500-line truncation) + `test_benchmark_preview.py`. |
| **Caching** | ✅ | `_UMAP_CACHE` in `arranger.py` and `@lru_cache` for WordNet in `wordnet.py`. |

## Concerns
- **Mock Fragility**: The test suite rely heavily on complex `MagicMock` setups (especially for WordNet and HDBSCAN). Significant time was spent fixing regressions caused by minor signature changes in mocks.
- **Dependency Versioning**: Had a conflict with `numpy >= 2.0` and `umap-learn`/`numba`, resolved by pinning `numpy < 2.4`. Future versions of specialized libraries may cause recursion.
- **Integration Test Environment**: `tests/test_integration_pipeline.py` is sensitive to internal logic changes in `imagenet.py`, requiring frequent manual patching of valid WNIDs.

## Recommendations
1. **Refactor Integration Tests**: Move away from complex `MagicMock` closures towards a local, minimal WordNet TSV mock if possible to reduce maintenance.
2. **Automated Performance Tracking**: Add a CI step that runs `tests/test_benchmark_preview.py` to ensure "Fast Preview" remains sub-second.
3. **Dependency Lockfile Integrity**: Continue using `uv` to manage the `.venv` to prevent "works on my machine" issues with `numpy`/`umap-learn`.

## Technical Debt to Address
- [ ] **Test Robustness**: Relax over-specified mock checks in `test_shaper.py` and `test_fast_preview.py`.
- [ ] **Centralized Mock fixtures**: Create a shared mock WordNet fixture instead of redefining it in every test file.
- [ ] **UI Polish**: The "Analysis" panel is still visible during long generations; could be swapped with a more detailed progress bar or logs.
