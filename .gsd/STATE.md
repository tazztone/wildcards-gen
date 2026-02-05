# Project State

## Current Position
- **Milestone**: v0.9.0-hardened
- **Phase**: 5 (Hardening & Quality)
- **Task**: Structural & Semantic Hardening
- **Status**: Paused at 2026-02-05 13:00

## Last Session Summary
Harden the wildcard generation pipeline by implementing a context-aware framework. Successfully resolved "Reactionary" label hallucination, eliminated redundant nesting (tautologies), and ensured YAML comment preservation.

## In-Progress Work
All hardening logic for Phase 5 is implemented and committed.
- Files modified: `arranger.py`, `shaper.py`, `wordnet.py`, `tencent.py`
- Tests status: Recently verified with regression scripts; full E2E run pending.

## Blockers
None.

## Context Dump
The system now treats hierarchy generation as a context-aware process rather than a pure mathematical clustering.

### Decisions Made
- **WordNet Prioritization**: Prioritize physical domain lexnames (food, animal, artifact) to avoid "People" synsets for common nouns (e.g., Bourbon).
- **Parent-Aware Naming**: The Arranger blacklists the parent name from being used as a child cluster label.
- **Recursive Shaper**: Tautology pruning is now recursive and handles sibling clashes by renaming to "General [Category]".
- **Conservative Flattening**: Preserves top-level semantic nodes even if they have only one child to maintain UX coherence.

### Approaches Tried
- **Sibling Merging**: Attempted to merge tautological children into the parent dict, but this caused YAML structural conflicts (list/dict mix). Resolved by "General" renaming.

### Current Hypothesis
The architectural interaction between Arranger (naming) and Shaper (pruning) is now stable. Full-scale datasets should no longer produce "Matter -> Wine" or "Wine -> Wine".

### Files of Interest
- `wildcards_gen/core/arranger.py`: Logic for context-aware naming.
- `wildcards_gen/core/shaper.py`: Recursive tautology and flattening logic.
- `wildcards_gen/core/wordnet.py`: Lexname prioritization logic.

## Next Steps
1. Perform a full E2E production run of Tencent ML-Images to verify all fixes at scale.
2. Prepare final audit report for v0.9.0-hardened.
3. Plan v1.0.0 Production Readiness.
