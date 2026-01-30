# SPEC.md — Project Specification

> **Status**: `FINALIZED`

## Vision
Stabilize the `wildcards-gen` codebase by resolving regression failures, unifying dependency management into a modern standards-based approach, and improving the interactive feedback loop in the GUI.

> [!NOTE]
> For detailed architectural principles (Skeleton concept, Smart Mode, Arranger logic), see [.gsd/ARCHITECTURE.md](file:///home/tazztone/_coding/wildcards-gen/.gsd/ARCHITECTURE.md).

## Goals
1.  **Data Science Core Upgrade**: Implement a strict DS pipeline (metrics, geometry-first clustering, deterministic naming) to generate high-quality, stable hierarchies.
2.  **Zero-Failure Test Suite**: Fix all regression failures in the pytest suite.
3.  **Unified Dependency Management**: Centralize requirements in `pyproject.toml`.
4.  **Rapid Settings Feedback**: Implement "Fast Preview" for pruning settings.

## Non-Goals (Out of Scope)
- Adding new raw datasets (Bio-Diversity, etc.) beyond the current set.
- Refactoring the LLM generation prompts.
- Migrating away from Gradio.

## Users
- **Data Scientists**: Who value stability metrics and clear taxonomy structures.
- **Power Users**: Who need to dial in specific pruning settings.
- **Maintainers**: Who need a stable build/test environment.

## Constraints
- **Python Version**: `>=3.10`.
- **Comment Preservation**: Must never compromise `ruamel.yaml` comment handling.
- **Reproducibility**: Taxonomy generation must be deterministic given the same inputs and seed.

## Success Criteria
- [ ] Stability metrics (Jaccard/Edit Distance) are implemented and reported.
- [ ] Clustering pipeline uses UMAP -> HDBSCAN for high-cardinality leaves.
- [ ] Group naming is deterministic (KeyBERT/TF-IDF) avoiding "Group N".
- [ ] `uv run pytest` passes 100% of tests.
