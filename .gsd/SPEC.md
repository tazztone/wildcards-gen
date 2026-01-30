# SPEC.md — Project Specification

> **Status**: `FINALIZED`

## Vision
Transform `wildcards-gen` from a robust engine into a polished, high-performance product. Focus on user feedback loops (fast previews), visual clarity (compact UI), and runtime efficiency (async/caching) to make the tool a joy to use.

> [!NOTE]
> This milestone focuses on **Interaction Design** and **Performance**. Core algorithms (Arranger/Shaper) are considered stable.

## Goals
1.  **Compact UI**: Redesign the "Analysis" and "Generation status" areas to maximize screen real estate for the important stuff (the hierarchy).
2.  **Performance Optimization**: Implement async execution for generation tasks to prevent GUI freezing.
3.  **Fast Previews**: Add "Dry Run" or "Preview" capability to see pruning effects without full generation.
4.  **Distribution**: Create a proper distribution build (PyPI package or simpler install) if feasible? (Optional)
    - *Correction*: Focus on local install experience first.

## Non-Goals
- New clustering algorithms.
- Changing the dataset parsers.

## Success Criteria
- [ ] UI "Analysis" section is collapsible or compact.
- [ ] Generation does not freeze the UI (Async/Threaded).
- [ ] Users can see a "Preview" of the hierarchy structure before saving.
