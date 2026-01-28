# Future Ideas Scheme

This document outlines potential future enhancements for the `wildcards-gen` project, focusing on semantic quality and automation.

## 1. Semantic Linter

**Goal:** Ensure generated lists are semantically consistent and free of outliers.

**Concept:**
- **Ambiguity Detection:** Identify terms that have multiple distinct meanings (polysemy) in the generated list context (e.g., "Crane" in a list of birds vs. construction equipment).
- **Outlier Detection:** Use lightweight embeddings (e.g., `all-MiniLM-L6-v2`) to flag items that are semantically distant from the cluster centroid.
- **Cluster Suggestion:** Detect if a list contains multiple distinct semantic clusters and suggest splitting it.

## 2. Dynamic Preset Auto-Tuning

**Goal:** Automate the tuning of Smart Mode parameters based on dataset characteristics, removing the need for manual overrides.

**Concept:**
- **Dry Run Analysis:** Before generation, perform a lightweight traversal to compute:
    1.  **Branching Factor Distribution:** Is the tree wide (OpenImages) or narrow?
    2.  **Depth Profile:** Is the tree deep (ImageNet) or shallow?
    3.  **Leaf Density:** Are leaves typically sparse or dense?
- **Adaptive Configuration:**
    - If **High Branching Factor (>500)**: Automatically increase `flattening_threshold`.
    - If **High Density**: Increase `min_leaf_size` to filter noise.
    - If **Shallow Depth**: Decrease `min_depth` protection to allow flattening.

## 3. Advanced Filtering

**Goal:** Provide more granular control over what gets included.

**Concept:**
- **Regex Filtering:** Allow users to exclude nodes matching specific patterns.
- **Subtree Exclusion:** partial selection of the tree (e.g. "Only generate `dog.n.01` and its children").

---


# Analysis Findings & Preset Tuning Report

## Executive Summary
This report analyzes the structural differences between `Compact`, `Flat`, and `Ultra-Flat` outputs across three datasets. The goal is to determine optimal preset parameters (`min_depth`, `flattening_threshold`, `min_leaf_size`) to create meaningful distinctions between presets for each specific dataset.

## Dataset Analysis

### 1. OpenImages Analysis
**Observations:**
- **Structure:** OpenImages is naturally broad but shallow in some areas, yet very deep in others (e.g., `entity -> abstraction ...`).
- **Response to Flattening:** 
  - `Compact` (525K) vs `Flat` (495K) showed very little difference (-5%).
  - This indicates that the default `Flat` threshold (500 items) is **too low** for OpenImages. Many category nodes likely exceed 500 descendants, preventing them from being flattened even in "Flat" mode.
- **Orphans:** The `merge_orphans` setting is critical here to prevent losing the "long tail" of specific object tags which are valuable for this dataset.

**Actionable Takeaway:**
- **Flat Preset:** Needs a significantly higher `flattening_threshold` (e.g., **1500**) to force flattening on its large sub-trees.
- **Compact Preset:** Should keep a moderate threshold (e.g., **200**) to preserve the semantic hierarchy which is quite good in OpenImages.

### 2. Tencent ML-Images Analysis
**Observations:**
- **Structure:** Extremely dense. A single node like `beverage` contains hundreds of items.
- **Response to Flattening:**
  - `Compact` (552K) vs `Flat` (348K) showed a massive difference (-37%).
  - The `Flat` preset successfully collapsed large sub-trees (e.g., `weather` removed, `beverage` flattened).
- **Risk:** "Ultra-Flat" can create list that are *too* large to be useful in a UI (1000+ items in a single dropdown).

**Actionable Takeaway:**
- **Flat Preset:** The current settings work well, but we should cap the density. `min_leaf_size` should be higher (e.g., **15**) to avoid creating "noise" lists.
- **Balanced Preset:** Needs to be distinct from Compact. Tencent's density means "Balanced" needs a higher threshold than ImageNet to show enough items.

### 3. ImageNet Analysis
**Observations:**
- **Structure:** Deep, taxonomic hierarchy (WordNet).
- **Response:** The standard presets work as the baseline here.
- **Compact:** Retains the classic `animal -> mammal -> carnivore` paths.
- **Flat:** Successfully merges the lower taxonomic ranks.

**Actionable Takeaway:**
- **Default Baseline:** Keep ImageNet settings as the universal defaults.

## Proposed Tuning Values (for `gui.py`)

| Dataset | Preset | Min Depth | Threshold (Max items) | Min Leaf | Merge Orphans | Reasoning |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **OpenImages** | **Compact** | 3 | **200** | 10 | True | Preserve structure, merge tiny noise. |
| **OpenImages** | **Flat** | **2** | **1500** | 15 | True | **Aggressive flattening** needed to affect this dataset. |
| **Tencent** | **Compact** | 3 | 100 | 10 | True | Keep structure, don't overwhelm. |
| **Tencent** | **Flat** | 2 | 600 | **20** | True | Flatten, but ensure resulting lists are substantial. |