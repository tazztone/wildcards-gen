---
phase: 1
plan: 1
wave: 1
---

# Plan 1.1: Async UI Foundation

## Objective
Decouple the GUI from the synchronous generation core. Currently, large generations freeze the browser interface. We will implement threaded execution with progress reporting to keep the UI responsive.

## Context
- .gsd/SPEC.md
- .gsd/ARCHITECTURE.md
- wildcards_gen/gui.py
- wildcards_gen/core/datasets/downloaders.py (Uses tqdm)

## Tasks

<task type="auto">
  <name>Implement ProgressCallback Protocol</name>
  <files>wildcards_gen/core/progress.py</files>
  <action>
    Create a `ProgressCallback` protocol/class that wraps `tqdm` for CLI and provides a hook for GUI.
    - Validate that core modules accept this callback instead of raw tqdm.
    - Refactor `downloaders.py` or `structure.py` to use it if needed.
  </action>
  <verify>grep -r "ProgressCallback" wildcards_gen/core/</verify>
  <done>Core modules support injected progress reporters</done>
</task>

<task type="auto">
  <name>Refactor GUI for Threaded Execution</name>
  <files>wildcards_gen/gui.py</files>
  <action>
    Modify the generation event handlers to use a generator function `yield`ing progress updates.
    - Use `gr.Progress` (Gradio's native progress bar) if supported, or a custom output box.
    - Wrap the `cli.generate_...` calls in a thread-safe manner.
  </action>
  <verify>grep "yield" wildcards_gen/gui.py</verify>
  <done>GUI updates text/progress bar during a long sleep payload (simulation)</done>
</task>

## Success Criteria
- [ ] Long generation tasks do not freeze the browser tab.
- [ ] Progress is visible in the GUI (e.g. "Processing... 45%").
