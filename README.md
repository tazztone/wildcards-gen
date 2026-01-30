
# Wildcards-Gen

**A unified CLI toolkit for generating hierarchical "skeleton" YAML files for AI image generation prompt management.**

This tool combines the precision of **WordNet** (for computer vision datasets) with the creativity of **LLMs** (for semantic categorization) to produce rich, context-aware taxonomies. It is designed to create the "skeleton" files used by the `wildcards-generator` SPA.

> [!TIP]
> **🎯 Looking for the Wildcards Generator SPA?** This CLI tool creates skeleton files for use with [**wildcards-generator**](https://github.com/tazztone/wildcards-generator) — the AI-powered web app that expands these skeletons into massive wildcard libraries.

## 🌟 How It Works

`wildcards-gen` is the **architect**. It builds the structural foundation that other tools populate.

```mermaid
flowchart LR
    A[wildcards-gen] -->|Generates| B(Skeleton YAML)
    B -->|Imported into| C[wildcards-generator SPA]
    C -->|AI Expansion| D[Massive Wildcard Sets]
    
    style A fill:#4CAF50,stroke:#333,stroke-width:2px
    style B fill:#FFC107,stroke:#333,stroke-width:2px
    style C fill:#2196F3,stroke:#333,stroke-width:2px
```

*   **You Provide**: A topic ("Fantasy RPG"), a dataset ("ImageNet"), or a raw list of terms.
*   **We Generate**: A nested YAML file where every category includes an `# instruction:` comment (e.g., "a medieval warrior specialized in melee combat"). Context is preserved even for dynamically generated clusters using **Instruction Injection**.
*   **The Result**: A context-rich structure specific enough to guide an AI, but broad enough to be populated with thousands of items.

---

## 🧠 Concept: Hybrid Taxonomy Induction

`wildcards-gen` solves the "messy ontology" problem. Raw dataset labels are often flat lists or technically deep but semantically noisy (e.g. `n02121808` -> `lion`).

We bridge this using a **Hybrid ML Approach**:
*   **Symbolic AI (WordNet)**: Provides the "prior" for structure and meaning. It tells us that a "Tabasco" is a type of "condiment".
*   **Statistical Semantics (Embeddings + HDBSCAN)**: Provides data-driven grouping. When WordNet fails or lists become too flat, we cluster items based on their vector similarity.

This "Taxonomy Induction + Structure Regularization" pipeline turns chaos into navigable, comment-preserving YAML skeletons.

---

## Key Features

### 🚀 Unified Workflow
One tool for all your taxonomy needs. Replaces disparate scripts with a robust CLI and GUI.

### 🧠 Hybrid Intelligence
*   **Dataset Mode (Deterministic)**: Extracts hierarchies from **ImageNet**, **COCO**, **Open Images**, and **Tencent**. Uses **WordNet glosses** for instructions.
*   **LLM Mode (Generative)**: Uses Large Language Models to categorize messy lists or create taxonomies from scratch.
*   **Semantic Arrangement**: Automatically groups flat lists (like "food items") into meaningful sub-clusters (e.g., "condiments", "fruits") using **Multi-Pass Clustering** and **Hybrid Naming** (e.g. `bird (eagle)` to avoid collisions).

### 🛡️ Robust & Verified
*   **Structure Preservation**: Built on `ruamel.yaml` to ensure instructions are never lost.
*   **Deep Hierarchies**: Supports arbitrary nesting depth.

### 🔍 How it generates:
1. **Download**: Grabs raw dataset metadata.
2. **Scan**: Maps IDs to physical names (e.g. "n02121808" -> "lion").
3. **Lookup**: Asks WordNet for a precise definition.
4. **Build**: Constructs a YAML file where every line has a built-in guide.

---

## 🛠️ Configuration

You can configure defaults via `wildcards-gen.yaml` in your project root or `~/.config/wildcards-gen/config.yaml`.

**Example `wildcards-gen.yaml`:**
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

## ⚡ Quick Start

### 1. Generate Skeletons (CV Datasets)
```bash
# Standard: ImageNet animals, 4 levels deep
wildcards-gen dataset imagenet --root animal.n.01 --depth 4 -o output/animals.yaml

# Smart Mode: Universal skeleton with semantic pruning (Recommended)
wildcards-gen dataset tencent --smart --preset balanced -o output/universal.yaml

# Open Images: Full 20k labels vs Legacy BBox
wildcards-gen dataset openimages --smart --preset detailed -o output/oi_full.yaml
wildcards-gen dataset openimages --bbox-only --smart -o output/oi_bbox.yaml
```

### 2. LLM Power Tools
```bash
# Categorize a raw text list
wildcards-gen categorize input/artists.txt -o output/art_styles.yaml

# Create from scratch
wildcards-gen create --topic "Magic Spells" -o output/magic.yaml

# Add instructions to legacy files
wildcards-gen enrich old_styles.yaml -o new_styles.yaml
```

### 3. Utilities
```bash
wildcards-gen lint output/skeleton.yaml
```

### 4. Visual GUI
Launch the web interface (Builder, Tools, Settings):
```bash
bash scripts/linux/run_gui.sh
# or
.\scripts\windows\run_gui.bat
```

---

## 🎚️ Smart Mode Tuning

Use `--preset` to control granularity.

| Preset | Details |
|--------|---------|
| `ultra-detailed` | Maximum depth, minimal pruning. |
| `detailed` | Good for specific domains (e.g. "Vehicles"). |
| `balanced` | **Recommended default.** |
| `compact` | Flattens redundant intermediates. |
| `flat` / `ultra-flat` | Highly compressed, few categories. |

<details>
<summary>Advanced: Fine-Tuning Parameters</summary>

| Flag | Default | Effect |
|------|---------|--------|
| `--min-depth` | `6` | Nodes shallower than this are always kept. |
| `--min-hyponyms` | `10` | Nodes with many descendants are kept. |
| `--min-leaf` | `3` | Small lists are merged upwards. |
| `--merge-orphans` | `True` | Merge pruned lists into context-aware keys (e.g. `other_bird`). |
| `--arrange-threshold` | `0.1` | Quality threshold for semantic grouping. |
| `--min-cluster` | `5` | Minimum size for a semantic sub-group. |
| `--skip-nodes` | `None` | Structural skipping (elision) of specific wrapper nodes. |
| `--orphans-label-template` | `None` | Template for orphan categories (e.g. `other_{}`). |

You can also use `--smart-config overrides.yaml` for granular subtree control.
</details>

---

## 🛠️ Installation & Setup

### 🚀 Easy Start (Recommended)
```bash
# Linux/macOS
bash scripts/linux/install.sh

# Windows
.\scripts\windows\install.bat
```

### 🧠 Quick Universal Skeleton
```bash
# Linux/macOS
bash scripts/linux/gen_universal.sh

# Windows
.\scripts\windows\gen_universal.bat
```

---

### Manual Installation
```bash
git clone https://github.com/tazztone/wildcards-gen.git
cd wildcards-gen

# Using uv (recommended)
uv venv .venv
source .venv/bin/activate
uv pip install -e .
```

---

## ❓ Common Questions

**Q: Do I need an API key for everything?**
**A:** No. All `dataset` commands (ImageNet, COCO, etc.) are **completely local and free**. You only need an API key for `create`, `categorize`, and `enrich`.

**Q: What's the difference between a category and a leaf?**
**A:** In the generated YAML:
   - **Categories** are dictionary keys. They get `# instruction:` comments to help the AI understand the context.
   - **Wildcards/Leaves** are list items. These are the actual values the AI will choose from.

**Q: Which LLM should I use?**
**A:** We default to `google/gemma-3-27b-it:free` on OpenRouter, which is very capable and free. If you need more precision for complex categorization, larger models may work better.

---

## 🔧 Troubleshooting & Tips

### 🐍 Python Version Error
If you see dependency resolution errors involving `transformers` or `sentence-transformers`, verify your Python version:
```bash
python --version  # (or `uv run python --version`) Must be >= 3.10
```
This is required for the Semantic Linter features.

### 🚫 Missing Categories (e.g., "Canine")
If a category you expect (like "canine") is missing or pruned, it's likely due to **WordNet Strictness**. WordNet's primary definition for "canine" is a *tooth*, not a dog. To tell the tool to be more permissive:
```bash
# Disable strict primary-synset checking
wildcards-gen dataset imagenet --no-strict ...
```

### 📦 Import Errors ("ModuleNotFoundError")
Always run the tool via `uv` or the installed script to ensure the environment is correct:
```bash
# ✅ CORRECT
uv run python -m wildcards_gen.cli ...

# ❌ INCORRECT (might use system python)
python wildcards_gen/cli.py ...
```

---

## 🗺️ Roadmap

Current status and planned features. We focus on **automation**, **structure architecture**, and **bulk processing**, leaving interactive editing and management to the [Wildcards Generator SPA](https://github.com/tazztone/wildcards-generator).

### ✅ Completed
- [x] Multi-dataset support (ImageNet, COCO, Open Images, Tencent)
- [x] Smart semantic pruning with configurable thresholds
- [x] LLM-powered taxonomy creation and enrichment
- [x] Gradio web GUI with dataset-aware UI
- [x] Comment-preserving YAML handling via ruamel.yaml
- [x] **Semantic Linter** — Analyze skeletons to detect semantically inconsistent items using embedding models
- [x] **Robustness Testing Suite** — Static & dynamic analysis to prevent UI/CLI/Mapping regressions

### 🚧 In Progress / Short-Term
- [ ] **Batch Pipeline** — Automated generation from a list of topics or roots (e.g. `input_topics.txt` → `multiple_skeletons/`)
- [ ] **Migration Utilities** — CLI tool to reverse-engineer legacy `.txt` wildcard folders into a single structured `.yaml` skeleton
- [ ] **Skeleton Merge/Split** — Tools to combine multiple skeletons or break a massive one into sub-modules

### 🔮 Planned / Long-Term
- [ ] **Custom Data Sources** — Plugins for Wikidata/DBpedia ingestion to complement WordNet
- [ ] **LLM Caching & Cost Optimization** — Local caching to minimize API usage during enrichment processes
- [ ] **CI/CD Integration** — Headless modes for validating skeleton integrity in build pipelines
- [ ] **Async/Parallel Processing** — Optimized engines for processing massive graph traversals (e.g. full WordNet exports)

### 💡 Ideas (Architecture & Data)
- **Domain Vocabularies**: Pre-packaged, curated WordNet subsets (e.g. "Bio-Diversity", "Fashion", "Military Hardware")
- **Auto-Enrichment**: recursive "deepening" of leaf nodes that are too broad

> Have a feature request? Open an issue on [GitHub](https://github.com/tazztone/wildcards-gen/issues)!

---

## 🔬 Semantic Intelligence

We use embedding models (Sentence Transformers) for both cleaning and organization.

### 1. Semantic Linter
Detects outliers in your wildcard lists. Items that are semantically inconsistent with their siblings are flagged for review.
```bash
# Lint a skeleton file
wildcards-gen lint output/skeleton.yaml --model minilm --threshold 0.2
```

### 2. Semantic Arrangement
Automatically discovers structure in flat lists. It uses **HDBSCAN** clustering to find sub-groups and **WordNet** logic to name them (e.g., finding that "basil, thyme, sage" -> "Herb").
*   **Multi-Pass Clustering**: Iteratively finds strong clusters then sweeps for smaller micro-clusters.
*   **Hybrid Naming**: Uses **Medoid Hypernyms** mixed with **Lowest Common Ancestors** to create descriptive, unique names like `bird (eagle)` vs `bird (hawk)`, avoiding generic numbering.
*   **Instruction Injection**: Dynamically constructs `# instruction:` comments for new clusters by aggregating definitions from WordNet.
*   **Determinism**: Uses a fixed seed and stable sorting to ensuring reproducible outputs.

### Available Models
| Model | Speed | Quality | Best For |
|-------|-------|---------|----------|
| `qwen3` | Slow | Best | Final review |
| `mpnet` | Medium | Good | General use |
| `minilm` | Fast | Acceptable | Quick checks |

### GUI
The Linter is also available in the GUI under the "🔬 Semantic Linter" tab. Upload a YAML file, select a model, and click "Run Linter" to see the report.