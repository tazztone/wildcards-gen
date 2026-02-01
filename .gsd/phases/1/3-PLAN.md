---
phase: 1
plan: 3
wave: 2
---

# Plan 1.3: Batch CLI & Multi-processing

## Objective
Implement a `batch` CLI command that processes multiple generation tasks in parallel using `ProcessPoolExecutor`. This enables high-throughput "Gold Standard" skeleton generation across different roots and datasets.

## Context
- .gsd/SPEC.md
- .gsd/phases/1/RESEARCH.md
- wildcards_gen/cli.py

## Tasks

<task type="auto">
  <name>Implement batch command in CLI</name>
  <files>wildcards_gen/cli.py</files>
  <action>
    Add a new `batch` sub-command to the CLI.
    
    Arguments:
    - `tasks.yaml`: A manifest file containing a list of generation requests.
    - `--workers`: Number of parallel processes to spawn.
    
    Manifest Format Example:
    ```yaml
    tasks:
      - dataset: imagenet
        root: n02084071 # dogs
        preset: balanced
      - dataset: tencent
        preset: compact
    ```
    
    Logic:
    1. Parse the manifest.
    2. Use `concurrent.futures.ProcessPoolExecutor` to map tasks to workers.
    3. Each worker task executes the corresponding `cmd_dataset_*` logic in isolation.
    4. Collect results and show a summary report.
  </action>
  <verify>wildcards-gen batch --help</verify>
  <done>Batch command is functional and can process multiple tasks in parallel.</done>
</task>

<task type="auto">
  <name>Unified Progress Tracking</name>
  <files>wildcards_gen/cli.py</files>
  <action>
    Integrate `tqdm` to show a unified progress bar for the batch execution.
    The bar should track "Tasks Completed" and optionally provide a sub-bar for the currently longest-running task (if possible with `tqdm` within processes).
  </action>
  <verify>Run a manifest with 3 tasks and check the progress display.</verify>
  <done>User gets clear visual feedback during parallel batch runs.</done>
</task>

## Success Criteria
- [ ] `wildcards-gen batch` can process multiple datasets in parallel.
- [ ] Sub-processes are isolated; a crash in one task does not kill the entire batch.
- [ ] Overall throughput scales with the number of available CPU cores.
