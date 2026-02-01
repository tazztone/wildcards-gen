---
phase: 1
plan: 2
wave: 1
---

# Plan 1.2: Threaded Recursion Parallelization

## Objective
Parallelize the recursive traversal in dataset modules (ImageNet, Tencent) using `ThreadPoolExecutor`. This allows simultaneous processing of sibling branches, particularly useful for the embedding/arrangement phase, while sharing the model instance in memory.

## Context
- .gsd/SPEC.md
- .gsd/phases/1/RESEARCH.md
- wildcards_gen/core/datasets/tencent.py
- wildcards_gen/core/datasets/imagenet.py

## Tasks

<task type="auto">
  <name>Implement parallel traversal in Tencent dataset</name>
  <files>wildcards_gen/core/datasets/tencent.py</files>
  <action>
    Update the recursive `build_commented` (or equivalent) function to process children in parallel threads.
    
    Logic:
    1. Only parallelize "heavy" nodes (those with many siblings or deep subtrees).
    2. Use `concurrent.futures.ThreadPoolExecutor` for sibling nodes.
    3. Ensure safe merging back into the `CommentedMap` (sequential mutation of the parent map after threads finish).
    4. Pass the shared `StatsCollector` safely.
    
    Threshold: Avoid threading for small groups (e.g. < 5 items) to minimize overhead.
  </action>
  <verify>python scripts/debug_manual_tencent.py</verify>
  <done>Tencent generation speed improved on multi-core systems without increased memory footprint.</done>
</task>

<task type="auto">
  <name>Implement parallel traversal in ImageNet dataset</name>
  <files>wildcards_gen/core/datasets/imagenet.py</files>
  <action>
    Apply similar `ThreadPoolExecutor` logic to `generate_imagenet_tree`.
    Focus on the recursive child processing loop.
    Ensure `WordNet` access remains stable (it is generally thread-safe for reading).
  </action>
  <verify>wildcards-gen dataset imagenet --smart --root n02084071 -o test.yaml</verify>
  <done>ImageNet generation utilizes threads for sibling branches.</done>
</task>

## Success Criteria
- [ ] Large dataset traversal is parallelized at the sibling level.
- [ ] Total generation time for a "Balanced" Tencent run is reduced by >= 40% on 4+ core systems.
- [ ] No race conditions in YAML assembly or stats collection.
