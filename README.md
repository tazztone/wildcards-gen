# wildcards-gen

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Lint](https://img.shields.io/badge/lint-ruff-purple)](https://docs.astral.sh/ruff/)
[![Types](https://img.shields.io/badge/types-mypy-blue)](https://mypy.readthedocs.io/)

A CLI + GUI toolkit for generating hierarchical skeleton YAML files for AI image generation prompt management. Combines WordNet (symbolic AI) with LLM-powered categorization to produce rich, context-aware taxonomies.

Designed as the **architect** half of the wildcard workflow — it builds structured skeletons that [wildcards-generator](https://github.com/tazztone/wildcards-generator) populates with AI-expanded content.

```mermaid
flowchart LR
    A[wildcards-gen] -->|Generates| B(Skeleton YAML)
    B -->|Imported into| C[wildcards-generator SPA]
    C -->|AI Expansion| D[Massive Wildcard Sets]
```

## Tech Stack

| Layer | Technology |
|---|---|
| Runtime | Python 3.10+ |
| CLI | argparse |
| GUI | Gradio |
| NLP / ML | NLTK (WordNet), Sentence Transformers, HDBSCAN, UMAP-learn, scikit-learn |
| YAML | ruamel.yaml (comment-preserving — do NOT use PyYAML) |
| Embedding cache | SQLite |
| LLM integration | OpenRouter (custom LLMEngine) |
| Linting | Ruff |
| Type checking | Mypy (100% coverage on core engines) |
| Testing | pytest + pytest-mock |
| Dependency management | uv |

## Architecture

```
wildcards_gen/
├── cli.py                  # Single argparse entry point
├── batch.py                # Batch processing logic
├── gui.py                  # Gradio web interface
└── core/
    ├── config.py           # Hierarchical configuration manager
    ├── structure.py        # ruamel.yaml wrapper (comment preservation)
    ├── llm.py              # OpenRouter integration + response cleaning
    ├── wordnet.py          # NLTK WordNet wrappers
    ├── smart.py            # Semantic pruning + leaf bubbling logic
    ├── arranger.py         # Recursive semantic clustering (UMAP + HDBSCAN)
    ├── shaper.py           # Post-processing constraints (orphan merging, flattening)
    ├── presets.py          # Pruning preset definitions
    ├── linter.py           # Semantic outlier detection
    ├── analyze.py          # Taxonomy analysis utilities
    ├── stats.py            # Telemetry + statistics
    └── datasets/           # Dataset-specific loaders (ImageNet, COCO, Open Images, Tencent)
```

## Key Features

- **Multi-dataset support** — ImageNet, COCO, Open Images, Tencent ML-Images (all free, no API key needed)
- **Hybrid taxonomy induction** — WordNet for structure + HDBSCAN/UMAP for data-driven clustering when WordNet fails
- **Smart pruning** — 5 presets from `ultra-flat` to `ultra-detailed`; linear chain collapse, orphan bubbling, self-reference filtering
- **LLM power tools** — `categorize` (messy list → hierarchy), `create` (topic → skeleton from scratch), `enrich` (add instructions to legacy files)
- **Semantic linter** — detects outlier items in wildcard lists using embedding similarity
- **Comment-preserving YAML** — `# instruction:` metadata survives all read/write cycles via `ruamel.yaml`
- **Gradio GUI** — Builder, Tools, Settings tabs with progressive disclosure

## Quick Start

### Easy install

```bash
# Linux/macOS
bash scripts/linux/install.sh

# Windows
.\scripts\windows\install.bat
```

### Manual install

```bash
git clone https://github.com/tazztone/wildcards-gen.git
cd wildcards-gen
uv venv .venv && source .venv/bin/activate
uv pip install -e .                    # Basic
uv pip install -e ".[analysis]"        # + semantic clustering
uv pip install -e ".[dev,analysis]"    # + dev tools
```

### Usage examples

```bash
# Generate skeleton from ImageNet (local, no API key)
wildcards-gen dataset imagenet --root animal.n.01 --depth 4 -o output/animals.yaml

# Smart mode with semantic pruning (recommended)
wildcards-gen dataset tencent --smart --preset balanced -o output/universal.yaml

# LLM: categorize a raw list
wildcards-gen categorize input/artists.txt -o output/art_styles.yaml

# LLM: generate from scratch
wildcards-gen create --topic "Magic Spells" -o output/magic.yaml

# Semantic lint check
wildcards-gen lint output/skeleton.yaml

# Launch GUI
bash scripts/linux/run_gui.sh
```

### Pruning presets

| Preset | Description |
|---|---|
| `ultra-detailed` | Maximum depth, minimal pruning |
| `detailed` | Good for specific domains |
| `balanced` | Recommended default |
| `compact` | Flattens redundant intermediates |
| `flat` / `ultra-flat` | Highly compressed, few categories |

## Configuration

`wildcards-gen.yaml` in project root or `~/.config/wildcards-gen/config.yaml`:

```yaml
api_key: "sk-or-..."                  # OpenRouter key (only for LLM commands)
model: "google/gemma-3-27b-it:free"   # Default: free Gemma on OpenRouter
paths:
  output_dir: "./output"
generation:
  default_depth: 3
  add_glosses: true
```

> Dataset commands (`imagenet`, `coco`, `openimages`, `tencent`) are fully local and require no API key.

## Development

```bash
# Lint
bash scripts/linux/lint.sh

# Tests
uv run pytest tests/
```

## License

MIT — see [LICENSE](LICENSE).
