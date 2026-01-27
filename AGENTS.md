
# Agent Instructions

## Project Overview

`wildcards-gen` is a unified tool for generating hierarchical wildcard skeletons. It merges the functionality of `Wildcards-Hierarchy-Generator` (CV datasets) and `wildcards-categorize` (LLM-based categorization).

## architectural Principles

1.  **Structure is Key**: We use `ruamel.yaml` via `StructureManager` for ALL YAML operations. Never use standard `yaml` or `PyYAML` as they strip comments. The `# instruction:` comments are the payload.
2.  **Hybrid Intelligence**: We prefer deterministic, free metadata (WordNet) first, and fallback/enhance with LLM (Generative) second.
3.  **Unified CLI**: All functionality is exposed via `wildcards-gen` subcommands defined in `wildcards_gen/cli.py`.

## Code Organization

-   `wildcards_gen/core/`: Application logic.
    -   `structure.py`: The `StructureManager` class. **CRITICAL**.
    -   `llm.py`: Interaction with OpenRouter/LLMs.
    -   `wordnet.py`: Shared WordNet logic.
    -   `datasets/`: Generators for specific datasets (ImageNet, COCO, OpenImages).
-   `wildcards_gen/prompts/`: Text files containing LLM prompts.
-   `tests/`: Unit tests using `pytest`.

## Contributing

-   When adding a new dataset, create a module in `core/datasets/` and expose it in `cli.py`.
-   Verify changes with `source .venv/bin/activate && pytest`.
-   Ensure all output YAMLs contain `# instruction:` comments.
