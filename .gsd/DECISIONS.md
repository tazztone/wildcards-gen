# DECISIONS.md

# Architecture & Design Decisions (ADR)

## 2026-01-30: Stabilization Pivot
**Context:** Existing codebase had several regression failures in tests and fragmented dependency management.
**Decision:** Prioritize codebase health over new features.
**Impact:** Will result in a 100% green test suite and a single source of truth for dependencies.

## 2026-01-30: Fast Preview Implementation
**Context:** Dataset generation for large datasets (Tencent/ImageNet) takes too long for iterative setting tuning.
**Decision:** Implement a "Preview Mode" that caps raw metadata parsing at 500 records.
**Impact:** GUI will become much more responsive for "dialing in" smart pruning parameters.
