
# Wildcards-Gen

**A unified CLI toolkit for generating hierarchical "skeleton" YAML files for AI image generation prompt management.**

This tool combines the precision of **WordNet** (for computer vision datasets) with the creativity of **LLMs** (for semantic categorization) to produce rich, context-aware taxonomies. It is designed to create the "skeleton" files used by the `wildcards-generator` SPA.

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
*   **We Generate**: A nested YAML file where every category includes an `# instruction:` comment (e.g., "a medieval warrior specialized in melee combat").
*   **The Result**: A context-rich structure specific enough to guide an AI, but broad enough to be populated with thousands of items.

---

## Key Features

### 🚀 Unified Workflow
One tool for all your taxonomy needs. Replaces disparate scripts with a robust CLI and GUI.

### 🧠 Hybrid Intelligence
*   **Dataset Mode (Deterministic)**: Extracts precise hierarchies from **ImageNet**, **COCO**, **Open Images**, and **Tencent ML-Images**. Uses **WordNet glosses** to automatically derive instructions.
*   **LLM Mode (Generative)**: Uses OpenRouter (default: `google/gemma-3-27b-it:free`) to categorize messy lists, create taxonomies from scratch, or "enrich" existing skeletons.

### 🛡️ Robust & Verified
*   **Structure Preservation**: Built on `ruamel.yaml` to ensure instructions are never lost.
*   **Deep Hierarchies**: Supports arbitrary nesting depth.

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

## 📖 Usage Guide & Examples

### 1. Generating form CV Datasets (WordNet)
*Best for: Realistic objects, animals, distinct physical concepts.*

**Scenario: Building a Creature Generator**
You want a massive list of animals, organized scientifically, with descriptions for an AI to use.
```bash
# Generate a hierarchy of all animals, 4 levels deep
wildcards-gen dataset imagenet --root animal.n.01 --depth 4 -o output/creatures.yaml
```

**Scenario: Massive Object Library**
You need general objects from a huge dataset.
```bash
wildcards-gen dataset tencent --depth 3 -o output/objects.yaml
```

### 2. LLM-Powered Creation
*Best for: Abstract concepts, fiction, artistic styles.*

**Scenario: Organizing a Messy List**
You have a text file `artists.txt` with 500 mixed artist names.
```bash
wildcards-gen categorize input/artists.txt -o output/art_styles.yaml
```

**Scenario: Designing a Magic System**
You want to invent a structure for "Magic Spells" from scratch.
```bash
wildcards-gen create --topic "Magic Spells and Incantations" -o output/magic.yaml
```

### 3. Enrichment
*Best for: Fixing generic wildcards.*

**Scenario: Improving Legacy Files**
You have an old YAML file that lacks instructions. The AI generates generic output because it doesn't know what "Synthwave" means.
```bash
# Adds "# instruction: A retro-futuristic aesthetic..." to every key
wildcards-gen enrich old_styles.yaml -o new_styles.yaml
```

### 4. Visual GUI
Prefer clicking? Launch the web interface:
```bash
wildcards-gen gui
```

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