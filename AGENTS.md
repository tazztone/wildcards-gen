
# Agent Instructions & Architecture

## Project Overview

`wildcards-gen` is the canonical tool for generating hierarchical wildcard skeletons. It represents a merger and maturity of previous experimental tools.

## Architectural Principles

### 1. The "Skeleton" Concept
This tool produces **skeletons**: structured YAML files with categories and instructions, but often minimal leaf nodes. These skeletons are imported into the `wildcards-generator` SPA, where the AI populates them with extensive wildcards.
*   **Goal**: precise structure, helpful context instructions.
*   **Non-Goal**: generating millions of wildcards (that's the SPA's job).

### 2. Strict Comment Preservation
The `# instruction:` comment is the payload. It tells the downhill AI what a category *means*.
*   **Implementation**: We use `ruamel.yaml` via the `StructureManager` class (`core/structure.py`).
*   **Rule**: NEVER use standard `yaml` or `PyYAML` libraries, as they strip comments.

### 3. Hybrid Data Sources
*   **WordNet (Trusted)**: Used for `dataset` commands. We map dataset IDs (WNID, Freebase) to WordNet Synsets to extract definitions.
*   **LLM (Flexible)**: Used for `categorize/create`. We use a custom `LLMEngine` that handles prompt loading and response cleaning (stripping markdown backticks).

## Codebase Organization

*   **`wildcards_gen/cli.py`**: The single entry point. Defined using `argparse`.
*   **`wildcards_gen/core/`**:
    *   `structure.py`: Wrapper for `ruamel.yaml` logic.
    *   `llm.py`: OpenRouter interaction. includes `_clean_response()` to fix markdown issues.
    *   `wordnet.py`: NLTK WordNet wrappers.
    *   `datasets/`: Logic for specific datasets (ImageNet, COCO, OpenImages).

## Maintenance & Contribution

*   **Adding Datasets**: Implement a new module in `core/datasets/` that returns a dictionary. Use `wordnet.py` to fetch glosses.
*   **Updating Prompts**: Edit text files in `wildcards_gen/prompts/`.
*   **Testing**: Run `pytest tests/`. Ensure any new LLM logic mimics the `_clean_response` pattern to handle API variances.

## Session Takeaways (Jan 2026)
*   **Open Images Fix**: The original generator produced flat lists. The new port ensures full hierarchy preservation.
*   **LLM Stability**: The `LLMEngine` must aggressively clean output (e.g. ` ```yaml `) to prevent parsing errors.
*   **Unified CLI**: Managing one tool is significantly easier than multiple scripts.
