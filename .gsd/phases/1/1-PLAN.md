---
phase: 1
plan: 1
wave: 1
---

# Plan 1.1: Persistent Embedding Cache (SQLite)

## Objective
Replace the transient in-memory `_EMBEDDING_CACHE` in `arranger.py` with a persistent SQLite database. This ensures that embeddings are shared across runs and processes, significantly reducing redundant computations during batch processing.

## Context
- .gsd/SPEC.md
- .gsd/phases/1/RESEARCH.md
- wildcards_gen/core/arranger.py

## Tasks

<task type="auto">
  <name>Implement PersistentEmbeddingCache class</name>
  <files>wildcards_gen/core/arranger.py</files>
  <action>
    Create a new class `PersistentEmbeddingCache` that manages an SQLite database.
    
    Logic:
    1. DB Location: Use `~/.cache/wildcards-gen/embeddings.db` or similar user-specific directory.
    2. Schema: `CREATE TABLE IF NOT EXISTS embeddings (term_hash TEXT PRIMARY KEY, model_name TEXT, embedding BLOB)`.
    3. Use WAL mode for concurrent access safety.
    4. Methods: `get(term, model_name)`, `set(term, model_name, embedding)`.
    5. Serialization: Store numpy arrays as binary BLOBs using `arr.tobytes()` and `np.frombuffer()`.
    
    Integration:
    - Replace the global `_EMBEDDING_CACHE` dictionary with an instance of this class.
    - Update `get_cached_embeddings` to use the persistence layer.
  </action>
  <verify>python -c "from wildcards_gen.core.arranger import PersistentEmbeddingCache; print('Persistent cache ready')"</verify>
  <done>Caching logic uses SQLite and survives process restarts.</done>
</task>

<task type="auto">
  <name>Add cache cleanup utility</name>
  <files>wildcards_gen/cli.py</files>
  <action>
    Add a new sub-command or flag to the `lint` command (or a new `cache` command) to clear the persistent cache.
    
    `wildcards-gen cache --clear`
    
    This provides a safety valve if the database grows too large or contains corrupted data.
  </action>
  <verify>wildcards-gen cache --clear --help</verify>
  <done>CLI allows clearing the persistent embedding cache.</done>
</task>

## Success Criteria
- [ ] Embeddings are persisted to disk in an SQLite database.
- [ ] Subsequent runs of the same dataset are significantly faster due to cache hits.
- [ ] CLI provides a way to manage/clear the cache.
