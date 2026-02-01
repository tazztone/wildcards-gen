# Design: Phase 2 - Interoperability

## Goal
Expand the tool's utility beyond human-readable YAML to support machine learning workflows (JSONL export) and customizable prompt engineering (templates).

## 1. JSONL Export
**User Story**: As an ML engineer, I want to export the generated hierarchy as a flat JSONL file so I can train a classification model or fine-tune an LLM.

### Format
Standard JSON Lines, where each line represents a single sample.
```json
{"text": "beagle", "label": "dog", "hierarchy": ["entity", "animal", "dog"]}
{"text": "poodle", "label": "dog", "hierarchy": ["entity", "animal", "dog"]}
```

### Implementation
- **Module**: `wildcards_gen/core/structure.py`
- **Method**: `StructureManager.save_structure(data, path, format='yaml')`
- **Logic**:
    - Recursive traversal to flatten the tree.
    - Collect path (hierarchy) for each leaf.
    - Write to `.jsonl` file.

### CLI
```bash
wildcards-gen dataset imagenet --format jsonl -o output.jsonl
```

## 2. Customizable Instruction Templates
**User Story**: As a prompt engineer, I want to control how the "gloss" is formatted in the YAML comment (e.g., `# instruction: ...` vs `# definition: ...`) so it matches my downstream tool's parser.

### Configuration
In `config.yaml` or CLI argument:
```yaml
generation:
  instruction_template: "# instruction: {gloss}"
  # Alternative: "# definition: {gloss} (WNID: {wnid})"
```

### Implementation
- **Module**: `wildcards_gen/core/structure.py` (and dataset generators)
- **Logic**:
    - Update `add_leaf_list` and `add_category_with_instruction` to accept a template or use global config.
    - Dataset generators currently format the string `f"# instruction: {gloss}"` manually. This needs to be centralized or passed down.
    - **Refactor**: Create `format_instruction(gloss, context)` helper in `structure.py`.

## Execution Plan
1.  **JSONL Support**:
    - Update `StructureManager` to support `save_as_jsonl`.
    - Update `cli.py` to accept `--format` argument.
    - Add tests (`tests/test_structure_extended.py`).

2.  **Instruction Templates**:
    - Add `instruction_template` to `Config`.
    - Refactor `imagenet.py`, `tencent.py`, `openimages.py` to use `format_instruction`.
    - Verify with a test run.
