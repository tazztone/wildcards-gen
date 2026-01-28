
# Agent Instructions & Architecture

## Project Overview

`wildcards-gen` is the canonical tool for generating hierarchical wildcard skeletons. It represents a merger and maturity of previous experimental tools.

**🎯 Target Tool:** [wildcards-generator](https://github.com/tazztone/wildcards-generator) — the AI-powered SPA that consumes the skeleton files produced by this CLI.

## Architectural Principles

### 1. The "Skeleton" Concept
This tool produces **skeletons**: structured YAML files with categories and instructions, but often minimal leaf nodes. These skeletons are imported into the `wildcards-generator` SPA, where the AI populates them with extensive wildcards.
*   **Goal**: precise structure, helpful context instructions.
*   **Non-Goal**: generating millions of wildcards (that's the SPA's job).
*   **Structure**:
    *   **Categories**: YAML dictionary keys. These receive `# instruction:` comments.
    *   **Wildcards/Leaves**: YAML list items. These are the actual prompt terms.

### 2. Strict Comment Preservation
The `# instruction:` comment is the payload. It tells the downhill AI what a category *means*.
*   **Implementation**: We use `ruamel.yaml` via the `StructureManager` class (`core/structure.py`).
*   **Rule**: NEVER use standard `yaml` or `PyYAML` libraries, as they strip comments.

### 3. Hybrid Data Sources
*   **WordNet (Trusted)**: Used for `dataset` commands. We map dataset IDs (WNID, Freebase) to WordNet Synsets to extract definitions.
*   **LLM (Flexible)**: Used for `categorize/create`. We use a custom `LLMEngine` that handles prompt loading and response cleaning (stripping markdown backticks).
*   **Prompt Pipeline**: `create` uses a two-phase prompt (Architect -> Mason). Architect defines the core roots; Mason fills in the sub-categories.

### 4. Smart Semantic Pruning
To prevent "directory bloat" and noisy hierarchies, the tool uses an intelligent pruning strategy (enabled via `--smart`):
*   **Semantic Significance**: Uses WordNet depth and branching factor to keep meaningful categories (e.g., "fruit") while flattening obscure intermediates.
*   **Linear Chain Removal**: Skips nodes that only have one child, consolidating them into the parent to reduce nesting depth.
*   **Minimum Leaf Size**: Small categories are merged upward to ensure every list in the skeleton has enough variety to be useful.
*   **Self-Reference Filtering**: Ensures leaf nodes never contain their own parent name (e.g., `nose:` instead of `nose: - nose`).

## Data Flow & State

1.  **Input**: raw strings (CLI), text files (categorize), or synset strings (ImageNet).
2.  **Processing**:
    *   `dataset_type` -> returns a `CommentedMap`.
    *   `LLM` -> returns a string, which is then parsed by `StructureManager.from_string()`.
3.  **Output**: All commands pass through `mgr.save_structure(data, path)` which ensures consistent formatting.

## LLM Logic (API Calls)

The `LLMEngine` interacts with OpenRouter using specific prompt templates located in `wildcards_gen/prompts/`:

*   **Structure Generation**: Takes sample terms and asks the LLM to design a hierarchy that "fits" them.
*   **Categorization**: Sends the full term list and the skeleton. Uses `response_format={"type": "json_object"}` to ensure the LLM returns a map of terms to categories.
*   **Enrichment**: A targeted prompt that tells the LLM to "fill in the gaps" for any keys missing an `# instruction:` comment.
*   **Cleaning**: The tool aggressively strips markdown code blocks (````yaml`, ` ``` `) from responses to prevent YAML parsing errors.

*   **`wildcards_gen/cli.py`**: The single entry point. Defined using `argparse`. Now includes `gui` subcommand and `SMART_PRESETS`.
*   **`wildcards_gen/gui.py`**: Gradio-based web interface. Includes `SMART_PRESETS` and `DATASET_PRESET_OVERRIDES` to customize defaults per dataset (e.g. OpenImages uses merge_orphans=True by default).
*   **`wildcards_gen/core/`**:
    *   `config.py`: Hierarchical configuration manager (CLI > Local > User > Env > Defaults).
    *   `structure.py`: Wrapper for `ruamel.yaml` logic.
    *   `llm.py`: OpenRouter interaction. Includes `_clean_response()` to fix markdown issues. Default model: `google/gemma-3-27b-it:free`.
    *   `wordnet.py`: NLTK WordNet wrappers.
    *   `smart.py`: Common logic for semantic pruning and leaf bubbling.
    *   `datasets/`: Logic for specific datasets (ImageNet, COCO, OpenImages, Tencent).

## Maintenance & Contribution

*   **Adding Datasets**: Implement a new module in `core/datasets/` that returns a dictionary. Use `wordnet.py` to fetch glosses.
*   **Updating Prompts**: Edit text files in `wildcards_gen/prompts/`.
*   **Testing**: Run `pytest tests/`. Ensure any new LLM logic mimics the `_clean_response` pattern to handle API variances.

## Technical Deep Dive: Trace of Execution

When a command like `wildcards-gen dataset tencent` is run, the backend follows this strictly orchestrated pipeline:

1.  **Orchestration (CLI & Config)**: `cli.py` initializes the `ConfigManager`, merging local/global YAML defaults with CLI overrides. It identifies the command and calls the appropriate generator.
2.  **Data Acquisition**: The `downloaders.py` module manages local caching. If a dataset (like Tencent's 11k categories) is missing, it streams it from source repositories to the `downloads/` directory.
3.  **Parsing & Graph Discovery**: Specific dataset modules (e.g., `tencent.py`) parse raw TSV/JSON files into a Directed Graph (mapping IDs, Names, and Parent-Child relationships).
4.  **Semantic Enrichment**: The builder recurses through the graph. For every node, it queries the local **NLTK WordNet** database via `wordnet.py`. It retrieves the "Gloss" (definition) using the WordNet ID.
5.  **Inline Structure Building & Smart Pruning**: We use `ruamel.yaml`'s `CommentedMap`. The builder evaluates each node's significance:
    *   **In Traditional Mode**: Truncates strictly at `max_depth`.
    *   **In Smart Mode**: Evaluates semantic value. If a node is significant and branching, it becomes a key; otherwise, its descendants are flattened into a leaf list.
6.  **Serialization**: The final structure is saved via `StructureManager`, ensuring that the complex `CommentedMap` is serialized back to clean YAML while preserving all metadata instructions and alphabetical sorting at every level.

## Session Takeaways (Jan 2026)
*   **Open Images Full Mode**: Implemented full support for 20,638 image-level labels (vs original ~600 bboxes). Uses dynamic WordNet mapping to build a deep hierarchy. Legacy bbox mode preserved via `--bbox-only`.
*   **Tencent ML-Images**: Added support for this massive dataset (11k categories) using text-only download logic.
*   **LLM Stability**: The `LLMEngine` must aggressively clean output (e.g. ` ```yaml `) to prevent parsing errors.
*   **Unified CLI**: Managing one tool is significantly easier than multiple scripts.
*   **Duplicate Wildcard Fix**: Resolved the `nose: - nose` issue by implementing strict self-reference filtering and empty-key output for leaves.
*   **Smart Semantic Logic**: Added WordNet-based depth and hyponym analysis to produce "meaningful" categories instead of arbitrary depth truncation.
*   **Smart Presets (Jan 28)**: Added 6 universal presets (`Ultra-Detailed` to `Ultra-Flat`) in both CLI (`--preset`) and GUI to simplify tuning.
*   **Orphan Bubbling (Jan 28)**: Fixed `min_leaf` logic in ImageNet/OpenImages to bubble small lists up to parent `misc:` key (matching Tencent logic) instead of discarding them.
*   **Dataset Overrides**: GUI now supports per-dataset preset overrides (e.g. OpenImages defaults to `merge_orphans=True` for better structure).
*   **Usability Improvements**: Implemented case-insensitive alphabetical sorting across all datasets to improve manual navigability.
