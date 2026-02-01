# Design: Batch Processing & Automated Analysis (Phase 1)

## Goal
Enable automated, high-throughput generation and analysis of multiple dataset configurations to facilitate "Smart Tuning" research.

## User Story
As a researcher, I want to define a "manifest" of experiments (e.g., testing different `semantic_threshold` values) and run them all in parallel, receiving a consolidated report of the results.

## CLI Command
```bash
wildcards-gen batch experiments.yaml --workers 4
```

## Manifest Format (YAML)
The manifest allows defining a base configuration and a list of jobs. It also supports simple **Matrix Expansion** for grid searches.

```yaml
# experiments.yaml
config:
  # Global defaults for all jobs
  output_dir: "experiments/2026-02-01_tuning"
  dataset: "tencent"
  analyze: true  # Run analysis report after generation?
  save_stats: true

# Option A: Explicit Job List
jobs:
  - name: "baseline"
    params:
      smart: true
      min_leaf_size: 20
      semantic_threshold: 0.1

  - name: "strict_clustering"
    params:
      smart: true
      min_leaf_size: 50
      semantic_threshold: 0.2

# Option B: Matrix (Grid Search)
# This generates jobs named "matrix_leaf50_thresh0.1", etc.
matrix:
  base_params:
    smart: true
  axes:
    min_leaf_size: [20, 50, 100]
    semantic_threshold: [0.1, 0.2, 0.3]
```

## Architecture

### 1. `BatchProcessor` (`wildcards_gen/batch.py`)
- **Responsibility**: Parses manifest, expands matrix, manages execution pool.
- **Concurrency**: Uses `ProcessPoolExecutor` (Multiprocessing) to bypass GIL, as dataset generation is CPU-intensive.
- **Progress**: Uses `tqdm` with `position` arguments to show multiple progress bars (or a single aggregated bar) without overlapping.

### 2. Job Execution
- Each job runs in a separate process.
- **Wrapper**: `run_job(job_config)`
  - Calls the appropriate core generator (e.g., `generate_tencent_hierarchy`) directly.
  - Catches exceptions to prevent crashing the whole batch.
  - Saves the YAML output.
  - (Optional) Runs `compute_dataset_stats` and saves `.stats.json`.

### 3. Consolidated Reporting
- After all jobs finish, the main process aggregates the `.stats.json` files.
- Generates a `summary.csv` or `report.md` comparing:
  - File size / Node count / Depth
  - Semantic outlier count (if linting enabled)
  - Execution time

## Integration Steps
1. Create `wildcards_gen/batch.py`.
2. Add `cmd_batch` to `cli.py`.
3. Refactor `cmd_dataset_*` logic slightly to ensure core generators are easily callable with a dict of params (they mostly are, via `**kwargs` or explicit args).

## Risks & Mitigations
- **Memory**: Running 4 concurrent Tencent generations might OOM.
  - *Mitigation*: Default `workers` to 1 or 2. User sets higher if they have RAM.
- **Model Loading**: Each process loading BERT/MiniLM is slow and wastes RAM.
  - *Mitigation*: Use the `PersistentEmbeddingCache` (SQLite) planned for Phase 1 so processes share the disk cache, though they still load models into RAM.
  - *Advanced Mitigation*: Use a separate "Embedding Server" process? (Overkill for now).
  - *Phase 1 Plan*: The SQLite cache in `arranger.py` will handle the embeddings sharing.

## Verification
- Create `tests/test_batch.py` using a mock generator and a small matrix.
