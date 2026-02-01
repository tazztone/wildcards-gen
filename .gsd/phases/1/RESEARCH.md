---
phase: 1
level: 2
researched_at: 2026-02-01
---

# Phase 1 Research: Throughput & Scaling

## Questions Investigated
1. **Parallelization Strategy**: How to parallelize the recursive traversal and embedding generation without hitting memory limits?
2. **Persistence**: How to share embeddings across runs and processes?
3. **Batch Mode**: What structure should the batch CLI command take?

## Findings

### 1. Hybrid Parallelism
- **Intra-run (Recursive)**: Recursive traversal in datasets (Tencent, ImageNet) is sibling-parallelizable. Using `ThreadPoolExecutor` is recommended here as it allows sharing a single model instance in memory, avoiding OOM for large models (Qwen3). `SentenceTransformer.encode` is thread-safe for inference.
- **Inter-run (Batch)**: Processing multiple distinct datasets/configs can use `ProcessPoolExecutor` for maximum throughput on multi-core systems.

**Recommendation**: 
- Implement a `ParallelExecutor` wrapper or simple `ThreadPoolExecutor` loop in the recursive `build_commented` functions.
- Use a `WorkerPool` for the new `batch` CLI command.

### 2. SQLite Embedding Cache
- The current in-memory `_EMBEDDING_CACHE` is lost after every run and not shared between processes.
- For batch mode, many terms will overlap (e.g., standard fruits, animals). Re-encoding them every time is a waste.
- **SQLite** is ideal: standard library, zero-conf, handles concurrent reads/writes well if used with WAL mode.

**Recommendation**: 
- Replace `_EMBEDDING_CACHE` in `arranger.py` with a `PersistentCache` class using SQLite.
- Schema: `term_hash (TEXT PRIMARY KEY), model_name (TEXT), embedding (BLOB)`.

### 3. Batch CLI Specification
- **Input**: A `manifest.yaml` (list of generation tasks) or a directory traversal.
- **Execution**: Parallel processing of tasks.
- **Feedback**: A unified progress bar showing `Tasks completed` and `Total items generated`.

## Decisions Made
| Decision | Choice | Rationale |
|----------|--------|-----------|
| Recursion Parallelism | Threading | Share model in memory; avoid multi-GB overhead per process. |
| Batch Parallelism | Multi-processing | Utilize all cores for distinct tasks; isolated failure domains. |
| Cache Storage | SQLite | Fast, persistent, concurrent-safe, no extra dependencies. |
| Cache Strategy | Content-Addressable | Use MD5 of term + model_name as key for stability. |

## Patterns to Follow
- **Sequential Mutation**: Only the parent thread should merge child branches into the `CommentedMap` to avoid `ruamel.yaml` race conditions.
- **Lazy Model Loading**: Load models only when first needed in the worker process.

## Anti-Patterns to Avoid
- **Deep Process Spawning**: Spawning processes inside recursive calls will lead to process explosion. Keep recursion parallelization at the thread level.
- **Global Memory Cache**: Avoid relying on global dictionaries in multi-process code.

## Dependencies Identified
| Package | Version | Purpose |
|---------|---------|---------|
| sqlite3 | (StdLib) | Persistent embedding cache |

## Risks
- **Memory Pressure**: Parallel threads calling `encode` simultaneously might spike RAM. Mitigation: Limit max workers based on available memory or CPU count.
- **Cache Bloat**: SQLite DB could grow large. Mitigation: Add a `lint --clear-cache` command.

## Ready for Planning
- [x] Questions answered
- [x] Approach selected
- [x] Dependencies identified
