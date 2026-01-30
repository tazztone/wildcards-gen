# SPEC.md — Project Specification

> **Status**: `FINALIZED`

## Vision
Stabilize the `wildcards-gen` codebase by resolving regression failures, unifying dependency management into a modern standards-based approach, and improving the interactive feedback loop in the GUI.

## Goals
1.  **Zero-Failure Test Suite**: Fix all regression failures in the pytest suite (Tencent ValueErrors, Config TypeErrors, and Dataset AssertionErrors).
2.  **Unified Dependency Management**: Centralize all project requirements (including `gradio` and ML libs) into `pyproject.toml` and remove the redundant `requirements.txt`.
3.  **Rapid Settings Feedback**: Implement a "Fast Preview" capability in the core dataset logic and GUI to allow users to tune smart-pruning settings on a 500-item subset before committing to a full generation.
4.  **Standardized Interfaces**: Ensure `apply_semantic_arrangement` and related core utilities have consistent return signatures across the codebase.

## Non-Goals (Out of Scope)
- Adding new datasets (Bio-Diversity, etc.).
- Refactoring the LLM generation prompts.
- Migrating from Gradio to another UI framework.

## Users
- **Power Users**: Who need to dial in specific pruning settings without waiting for 20,000-node graph traversals.
- **Maintainers**: Who need a stable build/test environment to prevent regressions.

## Constraints
- **Python Version**: Must remain `>=3.10` due to `transformers` dependency.
- **Comment Preservation**: Must never compromise `ruamel.yaml` comment handling.

## Success Criteria
- [ ] `uv run pytest` passes 100% of tests.
- [ ] `requirements.txt` is deleted and `pip install -e .` works fully.
- [ ] GUI includes a "Preview" toggle that limits dataset processing to the first 500 items.
- [ ] Build/CI scripts updated to reflect new dependency structure.
