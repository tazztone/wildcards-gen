# ROADMAP.md

> **Current Milestone**: v0.4.0 - Data Science Core
> **Goal**: Upgrade the taxonomy generation engine with strict data science methodologies (stability metrics, geometry-first clustering, deterministic naming) to produce high-quality, reproducible, and human-editable YAML artifacts.

## Must-Haves
- [ ] **Stability Metrics**: Measurable "diff stability" (Jaccard/Edit Distance) between runs.
- [ ] **Advanced Clustering**: UMAP → HDBSCAN pipeline for better separation in high-cardinality leaves.
- [ ] **Deterministic Naming**: Keyphrase extraction (TF-IDF/KeyBERT) to replace "Group N".
- [ ] **Hierarchical Leaves**: Recursive clustering for multi-level sub-categorization.
- [ ] **Constraints Engine**: Rule-based override system (must-link/cannot-link) for taxonomy shaping.

## Phases


### (No active phases)


---
## Archived Milestones

### v0.3.0 - UX Polish (Paused)
- [ ] Compact "Analysis" section to save vertical space.
- [ ] Move "Generation Completed" status to a fixed/prominent place.
