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

## 2026-02-05: Context-Aware Semantic Hierarchy
**Context:** The system was generating redundant hierarchies (Wine -> Wine) and "hallucinated" labels (Bourbon -> Reactionary).
**Decision 1 (Domain Prioritization):** In WordNet, explicitly prioritize `noun.food`, `noun.animal`, `noun.plant`, and `noun.artifact` lexnames over `noun.person`.
**Decision 2 (Parent-Aware Naming):** The `Arranger` must pass parent context down the tree and blacklist the parent's name from being used as a child cluster label.
**Decision 3 (General Renaming):** When a tautology cannot be flattened (due to siblings), rename the redundant child to `General [Parent]`.
**Decision 4 (Conservative Root Flattening):** Preserve top-level categories even if they have only one child, to maintain high-level semantic navigation.
**Impact:** Dramatic reduction in hierarchy noise and improved semantic coherence in generated wildcards.