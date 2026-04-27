# Wildcards-gen

Wildcards-gen is a unified CLI toolkit for generating hierarchical "skeleton" 
YAML files for AI image generation prompt management. This tool combines the 
precision of WordNet for computer vision datasets with the creativity of LLMs 
for semantic categorization to produce rich, context-aware taxonomies. 

Wildcards-gen is designed to create the "skeleton" files used by the 
`wildcards-generator` SPA.

<!-- prettier-ignore -->
> [!TIP]
> Looking for the Wildcards Generator SPA? This CLI tool creates skeleton files 
> for use with [wildcards-generator](https://github.com/tazztone/wildcards-generator) 
> — the AI-powered web app that expands these skeletons into massive wildcard 
> libraries.

## How it works

Wildcards-gen acts as the architect of your prompt taxonomies. It builds the 
structural foundation that other tools populate.

```mermaid
flowchart LR
    A[wildcards-gen] -->|Generates| B(Skeleton YAML)
    B -->|Imported into| C[wildcards-generator SPA]
    C -->|AI Expansion| D[Massive Wildcard Sets]
    
    style A fill:#4CAF50,stroke:#333,stroke-width:2px
    style B fill:#FFC107,stroke:#333,stroke-width:2px
    style C fill:#2196F3,stroke:#333,stroke-width:2px
```

When you provide a dataset (like ImageNet), a topic, or a raw list of terms, 
Wildcards-gen generates a context-rich skeleton:

- **Categories** (YAML Keys): These receive `# instruction:` comments to guide 
  the expansion process.
- **Wildcards** (YAML Lists): These are the actual prompt terms.

The resulting structure is specific enough to guide an AI but broad enough to 
support thousands of items.

---

## Hybrid taxonomy induction

Wildcards-gen solves the "messy ontology" problem by bridging raw dataset labels 
with semantic structures. Raw dataset labels are often flat lists or 
technically deep but semantically noisy (for example, `n02121808` -> `lion`).

We bridge this using a hybrid ML approach:

- **Symbolic AI (WordNet)**: Provides the prior for structure and meaning. For 
  example, it identifies that "Tabasco" is a type of "condiment".
- **Statistical Semantics (Embeddings + HDBSCAN)**: Provides data-driven 
  grouping. When WordNet fails or lists become too flat, we cluster items based 
  on their vector similarity.

This taxonomy induction and structure regularization pipeline turns chaos into 
navigable, comment-preserving YAML skeletons.

---

## Key features

Wildcards-gen provides a robust set of tools for managing AI image generation 
taxonomies through a unified workflow.

### Unified workflow

Wildcards-gen replaces disparate scripts with a robust CLI and GUI. It lets you 
manage all your taxonomy needs in one place.

### Hybrid intelligence

- **Dataset mode (Deterministic)**: Extracts hierarchies from ImageNet, COCO, 
  Open Images, and Tencent. Uses WordNet glosses for instructions.
- **LLM mode (Generative)**: Uses Large Language Models to categorize messy 
  lists or create taxonomies from scratch.
- **Semantic arrangement**: Automatically groups flat lists into meaningful 
  sub-clusters (for example, "condiments" or "fruits") using multi-pass 
  clustering and hybrid naming to avoid collisions.

### Robust and verified

- **Type Safety**: 100% Mypy coverage for core engines (`arranger`, `builder`, `shaper`).
- **Modern Linting**: Powered by Ruff for high-performance formatting and static analysis.
- **Structure preservation**: Built on `ruamel.yaml` to ensure instructions are 
  never lost. You must not use standard `PyYAML` on these files.
- **Smart pruning**: 
    - **Linear chain removal**: Automatically collapses categories with only one 
      child to reduce nesting fatigue.
    - **Structural skipping**: Prunes deep taxonomical wrapper nodes (for 
      example, "placental") while promoting their children.
    - **Orphan bubbling**: Merges tiny lists into parent-aware keys (for 
      example, `other_bird`) instead of discarding them.
    - **Self-reference filtering**: Prevents redundant entries by removing 
      leaves identical to their category name.
- **Semantic intelligence**: 
    - **Hybrid medoid naming**: Groups are named using the cluster's medoid 
      synset and hypernym (for example, `bird (eagle)`) to avoid generic 
      collisions.
    - **Instruction injection**: Automatically fetches WordNet definitions for 
      generated sub-groups.

### How it generates

Wildcards-gen follows a four-step process to generate skeletons:

1. **Download**: Retrieves raw dataset metadata.
2. **Scan**: Maps IDs to physical names.
3. **Lookup**: Queries WordNet for a precise definition.
4. **Build**: Constructs a YAML file where every line includes a built-in guide.

---

## Configuration

You can configure defaults via `wildcards-gen.yaml` in your project root or 
`~/.config/wildcards-gen/config.yaml`.

Example `wildcards-gen.yaml`:

```yaml
api_key: "sk-or-..."                  # OpenRouter Key
model: "google/gemma-3-27b-it:free"   # LLM Model

paths:
  output_dir: "./output"

generation:
  default_depth: 3
  add_glosses: true

datasets:
  imagenet:
    root_synset: "animal.n.01"        # Default root
```

---

## Quick start

The following examples demonstrate common tasks you can perform with 
Wildcards-gen.

### 1. Generate skeletons (CV datasets)

To generate skeletons from computer vision datasets:

```bash
# Standard: ImageNet animals, 4 levels deep
wildcards-gen dataset imagenet --root animal.n.01 --depth 4 -o output/animals.yaml

# Smart Mode: Universal skeleton with semantic pruning (Recommended)
wildcards-gen dataset tencent --smart --preset balanced -o output/universal.yaml

# Open Images: Full 20k labels vs Legacy BBox
wildcards-gen dataset openimages --smart --preset detailed -o output/oi_full.yaml
wildcards-gen dataset openimages --bbox-only --smart -o output/oi_bbox.yaml
```

### 2. LLM power tools

To use LLMs for categorization and creation:

```bash
# Categorize a raw text list
wildcards-gen categorize input/artists.txt -o output/art_styles.yaml

# Create from scratch
wildcards-gen create --topic "Magic Spells" -o output/magic.yaml

# Add instructions to legacy files
wildcards-gen enrich old_styles.yaml -o new_styles.yaml
```

### 3. Utilities

To lint a skeleton file:

```bash
wildcards-gen lint output/skeleton.yaml
```

### 4. Visual GUI

Launch the web interface to access the Builder, Tools, and Settings:

```bash
bash scripts/linux/run_gui.sh
# or
.\scripts\windows\run_gui.bat
```

---

## Smart mode tuning

Use the `--preset` flag to control the granularity of the generated taxonomy.

| Preset | Details |
|--------|---------|
| `ultra-detailed` | Maximum depth, minimal pruning. |
| `detailed` | Good for specific domains (for example, "Vehicles"). |
| `balanced` | Recommended default. |
| `compact` | Flattens redundant intermediates. |
| `flat` / `ultra-flat` | Highly compressed, few categories. |

<details>
<summary>Advanced: fine-tuning parameters</summary>

| Flag | Default | Effect |
|------|---------|--------|
| `--min-depth` | `6` | Nodes shallower than this are always kept. |
| `--min-hyponyms` | `10` | Nodes with many descendants are kept. |
| `--min-leaf` | `3` | Small lists are merged upwards. |
| `--merge-orphans` | `True` | Merge pruned lists into context-aware keys. |
| `--arrange-threshold` | `0.1` | Quality threshold for semantic grouping. |
| `--min-cluster` | `5` | Minimum size for a semantic sub-group. |
| `--skip-nodes` | `None` | Structural skipping of specific wrapper nodes. |
| `--orphans-label-template` | `None` | Template for orphan categories. |

You can also use `--smart-config overrides.yaml` for granular subtree control.
</details>

---

## Installation and setup

Wildcards-gen supports both automated and manual installation on Linux and 
Windows.

### Easy start (Recommended)

To install Wildcards-gen quickly:

```bash
# Linux/macOS
bash scripts/linux/install.sh

# Windows
.\scripts\windows\install.bat
```

### Quick universal skeleton

To generate a universal skeleton after installation:

```bash
# Linux/macOS
bash scripts/linux/gen_universal.sh

# Windows
.\scripts\windows\gen_universal.bat
```

---

### Manual installation

If you prefer manual installation:

1. Clone the repository:
   ```bash
   git clone https://github.com/tazztone/wildcards-gen.git
   cd wildcards-gen
   ```
2. Set up the environment using `uv`:
   ```bash
   uv venv .venv
   source .venv/bin/activate
   # Basic installation
   uv pip install -e .
   # With semantic features (clustering, UMAP, etc.)
   uv pip install -e ".[analysis]"
   # Developer setup (linting, testing)
   uv pip install -e ".[dev,analysis]"
   ```

---

## Common questions

### Do I need an API key for everything?

No. All `dataset` commands (ImageNet, COCO, etc.) are completely local and free. 
You only need an API key for `create`, `categorize`, and `enrich`.

### What's the difference between a category and a leaf?

In the generated YAML:

- **Categories** are dictionary keys. They get `# instruction:` comments to help 
  the AI understand the context.
- **Wildcards/Leaves** are list items. These are the actual values the AI will 
  choose from.

### Which LLM should I use?

We default to `google/gemma-3-27b-it:free` on OpenRouter, which is very capable 
and free. If you need more precision for complex categorization, larger models 
may work better.

---

## Troubleshooting and tips

### Python version error

If you see dependency resolution errors involving `transformers` or 
`sentence-transformers`, verify your Python version:

```bash
python --version  # (or `uv run python --version`)
```

The Python version must be 3.10 or higher. This is required for the semantic 
linter features.

### Missing categories

If an expected category is missing or pruned, it is likely due to WordNet 
strictness. For example, WordNet's primary definition for "canine" is a tooth, 
not a dog. To tell the tool to be more permissive, disable strict primary-synset 
checking:

```bash
wildcards-gen dataset imagenet --no-strict ...
```

### Import errors

Always run the tool via `uv` or the installed script to ensure the environment 
is correct:

```bash
# ✅ CORRECT
uv run python -m wildcards_gen.cli ...

# ❌ INCORRECT (might use system python)
python wildcards_gen/cli.py ...
```

---

## Design decisions and architecture

Wildcards-gen is built on a set of core architectural decisions to ensure 
consistency and semantic quality.

### Stabilization and quality

The project prioritizes codebase health and test coverage. This includes 
capping raw metadata parsing (for example, in the GUI) to ensure fast iterative 
tuning.

### Context-aware semantic hierarchy

To prevent "semantic hallucinations" (for example, mapping "Bourbon" to a 
political movement), the tool explicitly prioritizes domains like food, animal, 
plant, and artifact during WordNet lookups.

### Parent-aware naming

We implement naming logic that prevents tautologies (for example, `Wine -> Wine`). 
Redundant children are renamed to `General [Parent]` or bubbled up to ensure a 
cleaner hierarchy.

### Deep nesting preference

Wildcards-gen prefers deep, descriptive hierarchies (for example, 
`Food -> Beverage -> Alcohol -> Wine`) over flattened structures to provide 
better context for AI expansion.

---

## Technology stack

- **NLP/ML**: NLTK (WordNet), Sentence Transformers, HDBSCAN, UMAP-learn, 
  Scikit-learn.
- **Data**: SQLite (used for embedding caching to accelerate repeated runs), 
  `ruamel.yaml` (for comment-preserving YAML).
- **UI**: Gradio.
- **Testing**: Pytest with `pytest-mock`.

---

### Quality and verification

The project includes a comprehensive suite of automated tests and quality checks:

- **Type Safety (Mypy)**: Verified static types for all core modules.
- **Code Style (Ruff)**: Automated formatting and linting for consistency.
- **Interface synchronization**: Validates that GUI settings and CLI arguments 
  remain in sync.
- **Tooltip verification**: Programmatically checks that all UI elements have 
  descriptive help text.
- **Deep integration tests**: Full-stack end-to-end tests for dataset 
  generation.

To run the local verification suite:
```bash
bash scripts/linux/lint.sh
```

---

## Roadmap

Wildcards-gen focuses on automation, structure architecture, and bulk 
processing. Interactive editing and management are handled by the [Wildcards 
Generator SPA](https://github.com/tazztone/wildcards-generator).

### Completed

- [x] Multi-dataset support (ImageNet, COCO, Open Images, Tencent)
- [x] Smart semantic pruning with configurable thresholds
- [x] LLM-powered taxonomy creation and enrichment
- [x] Gradio web GUI with dataset-aware UI
- [x] Comment-preserving YAML handling via `ruamel.yaml`
- [x] **Semantic linter**: Analyze skeletons to detect outliers
- [x] **Developer Hardening**: Integrated Ruff/Mypy with CI enforcement

### Planned

- [ ] Centralize blacklist configuration.
- [ ] Implement regression tests for deep nesting.
- [ ] Streamline output logging (consolidate `.log` and `.json` stats).
- [ ] Perform E2E production run on Tencent ML-Images.

---

## Semantic intelligence

Wildcards-gen uses embedding models (Sentence Transformers) for both cleaning 
and organization.

### 1. Semantic linter

The semantic linter detects outliers in your wildcard lists. Items that are 
semantically inconsistent with their siblings are flagged for review.

```bash
# Lint a skeleton file
wildcards-gen lint output/skeleton.yaml --model minilm --threshold 0.2
```

### 2. Semantic arrangement

Semantic arrangement automatically discovers structure in flat lists. It uses 
HDBSCAN clustering to find sub-groups and WordNet logic to name them (for 
example, finding that "basil, thyme, sage" maps to "Herb").

- **Multi-pass clustering**: Iteratively finds strong clusters then sweeps for 
  smaller micro-clusters.
- **Hybrid naming**: Uses medoid hypernyms mixed with lowest common ancestors 
  to create descriptive, unique names (for example, `bird (eagle)` vs `bird 
  (hawk)`), avoiding generic numbering.
- **Instruction injection**: Dynamically constructs `# instruction:` comments 
  for new clusters by aggregating definitions from WordNet.
- **Determinism**: Uses a fixed seed and stable sorting to ensure reproducible 
  outputs.

### Available models

| Model | Speed | Quality | Best for |
|-------|-------|---------|----------|
| `qwen3` | Slow | Best | Final review |
| `mpnet` | Medium | Good | General use |
| `minilm` | Fast | Acceptable | Quick checks |

### GUI

The linter is also available in the GUI under the **🔬 Semantic Linter** tab. 
Upload a YAML file, select a model, and click **Run Linter** to see the report.

---

## Developer and agent architecture

This section provides technical documentation for contributing to or building on 
top of the Wildcards-gen engine.

### Core principles

#### 1. The skeleton concept

Wildcards-gen produces skeletons: structured YAML files with categories and 
instructions, but often minimal leaf nodes. These skeletons are imported into 
the `wildcards-generator` SPA, where the AI populates them with extensive 
wildcards.

- **Goal**: Precise structure and helpful context instructions.
- **Non-Goal**: Generating millions of wildcards (that's the SPA's job).

#### 2. Strict comment preservation

The `# instruction:` comment is the payload. It tells the downhill AI what a 
category means. We use `ruamel.yaml` via the `StructureManager` class 
(`core/structure.py`). You must not use standard `yaml` or `PyYAML` libraries, 
as they strip comments.

#### 3. Hybrid data sources

- **WordNet (Trusted)**: Used for `dataset` commands. We map dataset IDs (WNID, 
  Freebase) to WordNet Synsets to extract definitions.
- **LLM (Flexible)**: Used for `categorize/create`. We use a custom `LLMEngine` 
  that handles prompt loading and response cleaning.

#### 4. Smart mode pruning logic

- **Significance**: Uses WordNet depth and branching to keep meaningful 
  categories while flattening obscure intermediates.
- **Node elision**: Nodes in `SKIP_NODES` are logically removed while promoting 
  children.
- **Orphan bubbling**: Small lists are bubbled up to `other_{parent}:` keys.
- **Self-reference filtering**: Filters out leaf nodes that are identical to 
  their parent category name.

#### 5. Semantic arrangement (Arranger)

The arranger uses HDBSCAN-based density clusters with UMAP dimensionality 
reduction. It calculates the medoid, queries the hypernym, and appends the 
medoid if generic. Clusters are recursively processed to handle 
high-cardinality leaves.

#### 6. Constraint shaping (Shaper)

The shaper manages orphan merging and flattens unnecessary single-path nesting.

### Codebase map

- `wildcards_gen/cli.py`: The single entry point, defined using `argparse`.
- `wildcards_gen/batch.py`: Logic for batch processing and CLI support.
- `wildcards_gen/gui.py`: Gradio-based web interface.
- `wildcards_gen/core/`:
    - `config.py`: Hierarchical configuration manager.
    - `structure.py`: Wrapper for `ruamel.yaml` logic.
    - `llm.py`: OpenRouter interaction and response cleaning.
    - `wordnet.py`: NLTK WordNet wrappers.
    - `smart.py`: Common logic for semantic pruning and leaf bubbling.
    - `arranger.py`: Recursive semantic clustering (UMAP + HDBSCAN).
    - `shaper.py`: Post-processing constraints engine.
    - `presets.py`: Single source of truth for pruning presets.
    - `linter.py`: Semantic outlier detection logic.
    - `analyze.py`: Utilities for analyzing taxonomy structures.
    - `stats.py`: Statistics and telemetry collection.
    - `datasets/`: Logic for specific datasets.

### UI/UX principles (GUI)

- **Consolidated workflow**: Builder (Generation), Tools (Post-processing), and 
  Settings (Configuration).
- **Progressive disclosure**: Advanced tuning parameters are hidden behind 
  `gr.Accordion` by default.
- **Contextual help**: Uses `info=` arguments in Gradio components for 
  embedded documentation.

### Technical execution trace

When you run a command like `wildcards-gen dataset tencent`:

1. **Orchestration**: `cli.py` initializes the `ConfigManager` and identifies 
    the generator.
2. **Data acquisition**: `downloaders.py` manages local caching from source 
    repositories.
3. **Parsing**: Dataset modules parse raw files into a directed graph.
4. **Semantic enrichment**: The builder recurses through the graph, querying 
    WordNet for gloss definitions.
5. **Smart pruning**: Evaluates nodes for semantic significance, flattening 
    obscure nodes or bubbling orphans.
6. **Serialization**: `StructureManager` ensures the `CommentedMap` is 
    serialized back to clean YAML while preserving all metadata instructions.

### Maintenance and contribution

- **Adding datasets**: Implement a new module in `core/datasets/` that returns 
  a dictionary.
- **Testing**: Run `uv run pytest tests/` to ensure contract validation.
- **Requirements**: Python 3.10 or higher is required for the semantic linter 
  and arrangement features.
