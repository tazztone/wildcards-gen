---
phase: 2
level: 2
researched_at: 2026-01-30
---

# Phase 2 Research: UI Refresh & Feature Exposure

## Questions Investigated
1. Which core engine parameters are currently hardcoded/hidden from the user?
2. How to implement the requested "Compact UI" using Gradio 4 features?

## Findings

### Hidden Parameters
The following parameters are currently hardcoded in `arranger.py` or `smart.py` and need to be exposed:

| Parameter | Current Value | Target Location |
|-----------|---------------|-----------------|
| `umap_n_neighbors` | `15` | `SmartConfig` -> GUI |
| `umap_min_dist` | `0.1` | `SmartConfig` -> GUI |
| `umap_n_components` | `5` | `SmartConfig` -> GUI |
| `hdbscan_min_samples` | `= min_cluster_size` | `SmartConfig` -> GUI |
| `orphans_label_template` | `"misc"` (implicit) | `SmartConfig` -> GUI |

### UI Layout Options
Gradio 4.0+ supports `gr.Sidebar()`, which is perfect for the "Configuration" panel.
- **Current**: 2 Columns (50/50 split). Config takes up half the screen even when just viewing output.
- **Proposed**: `gr.Sidebar()` for Configuration. `gr.Column()` for Preview/Analysis.
    - **Benefit**: User can collapse settings to see full-width preview.

## Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Layout** | `gr.Sidebar` | Maximizes preview space while keeping controls accessible. |
| **Param Storage** | `SmartConfig` | Centralize all tuning in the config object rather than loose kwargs. |
| **Grouping** | "Advanced" Accordion | New params are niche; hide them by default to avoid overwhelming users. |

## Patterns to Follow
- **Config Propagation**: Update `SmartConfig.__init__` -> `dataset.generate_...` -> `arranger` -> `umap/hdbscan`.
- **Debounced Preview**: Ensure the new sliders trigger Fast Preview (if enabled).

## Dependencies Identified
- No new packages needed (Gradio, UMAP, HDBSCAN already installed).

## Setup for Phase 2
- [x] Parameters identified
- [x] Layout strategy selected
