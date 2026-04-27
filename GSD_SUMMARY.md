# Project Summary: wildcards-gen

This document summarizes the current state, architecture, and roadmap of the `wildcards-gen` project, distilled from the GSD framework data before its removal.

## 1. Project Vision & Goals
`wildcards-gen` is a tool designed to generate structured wildcard YAML files for AI image generation. It utilizes NLP (WordNet) and ML (embeddings, clustering) to transform flat lists of terms into semantic hierarchies.

**Key Goals:**
- **Reliability**: Focused "one-shot" generation with clear settings.
- **Semantic Coherence**: Meaningful hierarchy naming using WordNet LCAs (Lowest Common Ancestors).
- **Performance**: Support for large-scale datasets (ImageNet, Tencent ML-Images) via batch processing and parallelism.

---

## 2. Current Project State (as of 2026-04-27)
- **Status**: Milestone `v0.9.0-hardened`, Phase 5 (Hardening & Quality).
- **Current Task**: Centralized Taxonomy Logic (Plan 5.1).
- **Key Achievements**:
    - Batch processing and CLI support.
    - Parallelized embedding generation.
    - Smart Arrangement stability fixes (resolved duplication loops/data loss).
    - GUI refactor (2-column layout, removal of obsolete panels).

---

## 3. Architecture & Tech Stack

### Components
- **Core Logic (`wildcards_gen/core/`)**:
    - `arranger.py`: Semantic clustering (HDBSCAN/UMAP) and naming logic.
    - `shaper.py`: Post-processing, flattening, and constraint enforcement.
    - `wordnet.py`: NLTK WordNet integration for semantic lookups.
    - `config.py`: Centralized configuration.
- **Interfaces**:
    - `cli.py`: Batch/command-line operations.
    - `gui.py`: Gradio-based web interface.
- **Scripts**: Platform-specific runners and verification utilities.

### Technology Stack
- **Runtime**: Python >= 3.10
- **NLP/ML**: `nltk` (WordNet), `sentence-transformers`, `hdbscan`, `umap-learn`, `scikit-learn`.
- **UI**: `gradio`.
- **Data**: SQLite (for embedding caching), YAML (`ruamel.yaml`).
- **Testing**: `pytest`, `pytest-mock`.

---

## 4. Key Design Decisions (ADRs)
- **Stabilization Pivot (2026-01-30)**: Prioritize codebase health and test coverage over new features.
- **Fast Preview (2026-01-30)**: Cap raw metadata parsing at 500 records for iterative tuning in the GUI.
- **Context-Aware Semantic Hierarchy (2026-02-05)**:
    - Prioritize `food`, `animal`, `plant`, and `artifact` in WordNet.
    - Implement parent-aware naming to prevent tautologies (e.g., `Wine -> Wine`).
    - Rename redundant children to `General [Parent]` instead of simple flattening.
- **Root Validation**: Explicitly support "Matter" and "Substance" as valid roots (user preference).
- **Deep Nesting**: Prefer deep hierarchies (e.g., `Food -> Beverage -> Alcohol -> Wine`) over flattened structures.

---

## 5. Roadmap & Future Work
- **Milestone v1.0.0 (Planned)**: Production readiness.
    - Final performance audit for 1M+ items.
    - Installation wizard (Windows/Linux).
    - Comprehensive API documentation.
- **Pending Tasks**:
    - [ ] Complete Plan 5.1: Centralize blacklist config and add regression tests for deep nesting.
    - [ ] Remove redundant `.log` files (identical information is in `.json` stats).
    - [ ] E2E production run on Tencent ML-Images.

---

## 6. Quality & Verification
The project has undergone rigorous audits and verification sessions:
- **Milestone v0.8.0 Audit**: Focused on stability and UI polish. Successfully resolved critical `TypeError` regressions and streamlined the Gradio interface.
- **Automated Verification**:
    - `tests/test_interface_sync.py`: Validates signature consistency between GUI and backend.
    - `tests/test_gui_registry.py`: Programmatically verifies that all UI settings have descriptive tooltips.
    - `tests/test_deep_integration.py`: Full-stack E2E tests for dataset generation.

## 7. Technical Debt & Lessons Learned
- **UI Logic Maintenance**: Structural changes to the Gradio interface (like removing the Analysis panel) require careful updates to UI logic tests (e.g., return count adjustments).
- **Silent UX Quality**: Tooltips should be programmatically verified to prevent "detached" or missing guidance when settings change.
- **Log Management**: The project currently generates redundant `.log` files alongside `.json` statistics; these are slated for removal to clean up output directories.
- **Semantic Hallucinations**: Previous versions suffered from "hallucinated" labels (e.g., mapping Bourbon to Reactionary). This was fixed by explicitly prioritizing food/animal/plant domains in WordNet lookups.
