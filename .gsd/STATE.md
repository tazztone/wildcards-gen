# State - Milestone v0.9.0 [IN PROGRESS]

## Current Position
- **Phase**: 2 (Interoperability)
- **Task**: Finalization
- **Status**: Completed

## Last Session Summary
- **Phase 2 (Completed)**:
    - **JSONL Export**: Implemented and verified via `StructureManager` and CLI.
    - **Templates**: Centralized instruction formatting in `config.py` and refactored all dataset generators to use it.
    - **Verification**: Passed `test_structure_extended.py` and CLI smoke tests for COCO (JSONL & YAML).

## In-Progress Work
- Ready for release or next milestone.

## Context Dump

### Decisions Made
- **JSONL**: Flattens hierarchy to `{"text": "term", "label": "parent", "hierarchy": ["p", "c"]}`.
- **Templates**: Default is `"instruction: {gloss}"`. `ruamel.yaml` handles the `#`.

### Files of Interest
- `wildcards_gen/core/structure.py`
- `wildcards_gen/core/config.py`
- `wildcards_gen/cli.py`

## Next Steps
1. Release v0.9.0.
