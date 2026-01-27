
# Wildcards-Gen

**A unified CLI toolkit for generating hierarchical "skeleton" YAML files for AI image generation prompt management.**

This tool combines the precision of **WordNet** (for computer vision datasets) with the creativity of **LLMs** (for semantic categorization) to produce rich, context-aware taxonomies. It is designed to create the "skeleton" files used by the `wildcards-generator` SPA.

## Key Takeaways & Features

### 🚀 Unified Workflow
Replaces disparate scripts (`Wildcard-Hierarchy-Generator`, `wildcards-categorize`) with a single, robust CLI: `wildcards-gen`. One tool for all your taxonomy needs.

### 🧠 Hybrid Intelligence
*   **Dataset Mode (Deterministic)**: Extracts precise hierarchies from **ImageNet**, **COCO**, **Open Images**, and **Tencent ML-Images**. Uses **WordNet glosses** to automatically generate `# instruction:` comments (e.g., "a living organism characterized by voluntary movement" for *animal*).
*   **LLM Mode (Generative)**: Uses OpenRouter (default: `google/gemma-3-27b-it:free`) to categorize messy lists, create taxonomies from scratch, or "enrich" existing skeletons with better descriptions.

### 🛡️ Robust & Verified
*   **Structure Preservation**: Built on `ruamel.yaml` to ensure `# instruction:` comments are never lost during processing.
*   **Markdown Cleaning**: Automatically strips markdown backticks from LLM responses, ensuring valid YAML output every time.
*   **Deep Hierarchies**: Fully supports nested structures. *Note: Open Images and Tencent generation produce proper trees, not flat lists.*

---

## Installation

```bash
git clone https://github.com/tazztone/wildcards-gen.git
cd wildcards-gen

# Using uv (recommended)
uv venv .venv
source .venv/bin/activate
uv pip install -e .
```

---

## Usage Guide

### 1. Generating form CV Datasets (WordNet)

Best for creating solid, grounded baselines from massive datasets.

**COCO (Quick Start)**
```bash
wildcards-gen dataset coco -o output/coco.yaml
```

**ImageNet (Deep Custom Trees)**
```bash
# Generate a tree for "musical instrument" (depth 3)
wildcards-gen dataset imagenet --root musical_instrument.n.01 --depth 3 -o output/instruments.yaml
```

**Tencent ML-Images (Massive Scale)**
```bash
wildcards-gen dataset tencent --depth 3 -o output/tencent.yaml
```

**Open Images**
```bash
wildcards-gen dataset openimages -o output/openimages.yaml
```

### 2. GUI Mode (New!)

Prefer a visual interface? Launch the local web app to generate skeletons interactively:
```bash
wildcards-gen gui
```
*Features: Dropdown selector, depth slider, instant preview, and download.*

### 3. LLM-Powered Commands

Requires `OPENROUTER_API_KEY` environment variable.
Defaults to `google/gemma-3-27b-it:free` for cost-free operation.

**Create from Scratch**
Generate a full taxonomy for any topic:
```bash
wildcards-gen create --topic "Fantasy RPG Classes" -o output/rpg.yaml
```

**Categorize a List**
Turn a flat text file (`input/terms.txt`) into a hierarchy:
```bash
wildcards-gen categorize input/terms.txt -o output/categorized.yaml
```

**Enrich Existing Files**
Add or improve `# instruction:` comments in any YAML file:
```bash
wildcards-gen enrich output/legacy_file.yaml -o output/enriched.yaml
```

---

## Output Format

The tool generates YAML perfectly formatted for `wildcards-generator`, with context instructions preserved:

```yaml
animal: # instruction: a living organism characterized by voluntary movement
  canines: # instruction: carnivorous mammals of the family Canidae
    - dog
    - wolf
  felines: # instruction: mammals of the family Felidae
    - cat
    - lion
```