
# Wildcards-Gen

A unified CLI toolkit for generating hierarchical "skeleton" YAML files for AI image generation prompt management.

Combines the power of **WordNet** (for computer vision datasets) and **LLMs** (for semantic categorization) to produce rich, structured taxonomies with `# instruction:` comments.

## Features

- **Unified Tool**: Replaces disparate scripts with a single `wildcards-gen` CLI.
- **Instruct-Ready Output**: Automatically adds `# instruction:` comments to YAML categories, enabling context-aware AI expansion in downstream tools like `wildcards-generator`.
- **Hybrid Intelligence**:
    - **WordNet Mode**: Uses lexical database definitions for standard datasets (ImageNet, COCO, Open Images) - Fast, free, precise.
    - **LLM Mode**: Uses OpenRouter (e.g., GPT-4o) for arbitrary term lists or instruction enrichment - Creative, flexible, smart.
- **Structure Preservation**: Uses `ruamel.yaml` to ensure comments and structure are perfectly preserved.
- **Smart Datasets**:
    - **ImageNet**: Generate trees from any root synset.
    - **Open Images**: Full hierarchy support (no more flat lists).
    - **COCO**: Standardized 80-class hierarchy.

## Installation

```bash
git clone https://github.com/tazztone/wildcards-gen.git
cd wildcards-gen

# Using uv (recommended)
uv venv .venv
source .venv/bin/activate
uv pip install -e .
```

## Usage

### 1. Generating from Standard Datasets

Generate a skeleton from **COCO** (fastest start):
```bash
wildcards-gen dataset coco -o output/coco.yaml
```

Generate from **ImageNet** (deep hierarchy):
```bash
# Generate animal taxonomy
wildcards-gen dataset imagenet --root animal.n.01 --depth 3 -o output/animals.yaml
```

Generate from **Open Images**:
```bash
wildcards-gen dataset openimages -o output/openimages.yaml
```

### 2. Categorizing Custom Lists (LLM)

If you have a flat text file of terms (`input/monsters.txt`):
```bash
export OPENROUTER_API_KEY=sk-...
wildcards-gen categorize input/monsters.txt -o output/monsters.yaml
```

### 3. Creating New Taxonomies (LLM)

Create a structure from scratch for a topic:
```bash
wildcards-gen create --topic "Fantasy RPG Classes" -o output/rpg.yaml
```

### 4. Enriching Instructions (LLM)

Improve the `# instruction:` comments in any existing YAML:
```bash
wildcards-gen enrich output/old_structure.yaml
```

## Output Format

The tool generates YAML compatible with `wildcards-generator`:

```yaml
canines: # instruction: carnivorous mammals of the family Canidae
  - dog
  - wolf
  - fox
felines: # instruction: mammals of the family Felidae
  - cat
  - lion
```