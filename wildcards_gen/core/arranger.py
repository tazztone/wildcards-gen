"""
Semantic Arrangement Logic.

Uses embedding models and clustering (HDBSCAN) to automatically group
flat lists of terms into meaningful sub-categories.

Key features:
- Caches embeddings to speed up repeated runs
- Uses WordNet LCA (Lowest Common Ancestor) for naming
- Robust fallback naming ("Group 1", "Group 2") for generic clusters
"""

import logging
import re
from typing import List, Dict, Tuple, Optional
import functools
import hashlib

from .wordnet import get_primary_synset, get_synset_name, is_abstract_category
from .linter import check_dependencies, load_embedding_model, compute_list_embeddings, get_hdbscan_clusters

logger = logging.getLogger(__name__)

# In-memory cache for embeddings (hash(term_list) -> embeddings)
_EMBEDDING_CACHE = {}

def get_cached_embeddings(model, terms: List[str]):
    """Get embeddings with simple in-memory caching."""
    # Create valid hashable key
    key_str = "|".join(sorted(terms))
    key_hash = hashlib.md5(key_str.encode('utf-8')).hexdigest()
    
    if key_hash in _EMBEDDING_CACHE:
        return _EMBEDDING_CACHE[key_hash]
        
    embeddings = compute_list_embeddings(model, terms)
    _EMBEDDING_CACHE[key_hash] = embeddings
    return embeddings

def normalize_term(term: str) -> str:
    """Normalize term for stable processing."""
    return term.lower().strip()

def get_lca_name(terms: List[str]) -> Optional[str]:
    """
    Find the Lowest Common Ancestor name for a group of terms using WordNet.
    Returns None if no common ancestor found or if too generic.
    """
    if not terms:
        return None
        
    synsets = []
    for t in terms:
        s = get_primary_synset(t)
        if s:
            synsets.append(s)
            
    if len(synsets) < 2:
        return None
        
    # Find LCA
    # NLTK's lowest_common_hypernyms works on pairs.
    # We iteratively find LCA of the set.
    current_lca = synsets[0]
    for s in synsets[1:]:
        lcas = current_lca.lowest_common_hypernyms(s)
        if not lcas:
            return None
        current_lca = lcas[0]
        
    name = get_synset_name(current_lca)
    
    # Blacklist check
    # Abstract or too generic terms
    BLACKLIST = {
        'entity', 'physical entity', 'abstraction', 'object', 'whole', 
        'matter', 'metric unit', 'unit', 'causal agent', 'variable',
        'substance', 'matter', 'group'
    }
    
    if name.lower() in BLACKLIST or is_abstract_category(current_lca):
        return None
        
    return name

import numpy as np
from sklearn.metrics.pairwise import euclidean_distances

# ... imports ...

def get_medoid_name(cluster_embeddings: np.ndarray, cluster_terms: List[str]) -> Optional[str]:
    """
    Finds the medoid (term closest to centroid) and asks WordNet for its hypernym.
    """
    if not cluster_terms:
        return None
        
    try:
        # 1. Compute Centroid
        centroid = np.mean(cluster_embeddings, axis=0)
        
        # 2. Find Medoid (closest term to centroid)
        distances = euclidean_distances([centroid], cluster_embeddings)
        medoid_idx = np.argmin(distances)
        medoid_term = cluster_terms[medoid_idx]
        
        # 3. Get WordNet Hypernym of the medoid
        synset = get_primary_synset(medoid_term)
        if synset:
            hypernyms = synset.hypernyms()
            if hypernyms:
                # Use the first hypernym
                name = get_synset_name(hypernyms[0])
                if name and name.lower() not in {'entity', 'object', 'whole'}:
                    return name
                    
        return None # Fallback
    except Exception as e:
        logger.warning(f"Medoid naming failed: {e}")
        return None


def _arrange_single_pass(
    terms: List[str],
    embeddings: np.ndarray,
    min_cluster_size: int,
    threshold: float,
    cluster_selection_method: str = 'eom',
    min_samples: Optional[int] = None
) -> Tuple[Dict[str, List[str]], List[str], Dict]:
    """
    Internal Helper: Run a single pass of HDBSCAN clustering.
    Returns: (groups, leftovers, stats)
    """
    import hdbscan
    
    # Defaults
    if min_samples is None:
        min_samples = min_cluster_size
        
    stats = {
        "n_clusters_found": 0,
        "n_clusters_rejected": 0,
        "noise_ratio": 0.0,
        "details": []
    }
        
    if len(terms) < min_cluster_size + 1:
        return {}, terms, stats

    try:
        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=min_cluster_size, 
            min_samples=min_samples,
            gen_min_span_tree=True,
            cluster_selection_method=cluster_selection_method
        )
        clusterer.fit(embeddings)
        labels, probabilities = clusterer.labels_, clusterer.probabilities_
    except Exception as e:
        logger.warning(f"HDBSCAN error: {e}")
        return {}, terms, stats

    # Process clusters
    clusters: Dict[int, List[int]] = {}
    for idx, label in enumerate(labels):
        if label != -1:
            if label not in clusters: clusters[label] = []
            clusters[label].append(idx)
            
    # Stats
    noise_count = list(labels).count(-1)
    stats["noise_ratio"] = noise_count / len(labels)
    stats["n_clusters_found"] = len(clusters)

    named_groups = {}
    used_indices = set()
    
    # Sort for stability
    sorted_labels = sorted(clusters.keys(), key=lambda l: len(clusters[l]), reverse=True)
    fallback_counter = 1

    for label in sorted_labels:
        indices = clusters[label]
        probs = [probabilities[i] for i in indices]
        mean_prob = sum(probs) / len(probs)
        
        cluster_items = [terms[i] for i in indices]
        
        # Diagnostic Detail
        stats["details"].append({
            "size": len(indices),
            "mean_prob": round(mean_prob, 3),
            "accepted": mean_prob >= threshold,
            "sample": cluster_items[:3]
        })
        
        if mean_prob < threshold:
            stats["n_clusters_rejected"] += 1
            continue

        # Naming Strategy
        # 1. Try LCA
        name = get_lca_name(cluster_items)
        
        # 2. Try Medoid Hypernym (New)
        if not name:
            cluster_embs = embeddings[indices]
            name = get_medoid_name(cluster_embs, cluster_items)
            
        # 3. Fallback
        if not name:
            name = f"Group {fallback_counter}"
            fallback_counter += 1
            
        # Unique naming
        original_name = name
        counter = 2
        while name in named_groups:
            name = f"{original_name} {counter}"
            counter += 1
            
        named_groups[name] = sorted(cluster_items)
        used_indices.update(indices)
        
    leftovers = [t for i, t in enumerate(terms) if i not in used_indices]
    return named_groups, sorted(leftovers), stats


def arrange_list(
    terms: List[str], 
    model_name: str = "minilm", 
    threshold: float = 0.1, 
    min_cluster_size: int = 5,
    cluster_selection_method: str = 'eom',
    return_stats: bool = False
) -> Tuple[Dict[str, List[str]], List[str], Optional[Dict]]:
    """
    Arrange a flat list into semantic sub-groups using Multi-Pass Clustering.
    """
    if not terms or len(terms) < 3:
        if return_stats:
            return {}, terms, {}
        return {}, terms
        
    if not check_dependencies():
        if return_stats:
            return {}, terms, {"error": "missing_dependencies"}
        return {}, terms

    # 1. Embeddings (Computed Once)
    model = load_embedding_model(model_name)
    normalized = [normalize_term(t) for t in terms]
    embeddings = get_cached_embeddings(model, normalized)
    
    if len(embeddings) == 0:
        if return_stats:
            return {}, terms, {"error": "no_embeddings"}
        return {}, terms

    # --- PASS 1: Main Configured Pass ---
    groups_1, leftovers_1, stats_1 = _arrange_single_pass(
        terms, embeddings, 
        min_cluster_size=min_cluster_size, 
        threshold=threshold,
        cluster_selection_method=cluster_selection_method
    )
    
    final_groups = groups_1
    final_leftovers = leftovers_1
    
    # --- PASS 2: "Cleanup" on Leftovers ---
    # Only if leftovers are substantial to avoid fragmented noise
    # and if the user isn't already using strict settings (min_size=2)
    stats_2 = None
    if len(final_leftovers) > 20 and min_cluster_size > 2:
        
        # Determine indices of leftovers in original list to slice embeddings
        leftover_indices = [i for i, t in enumerate(terms) if t in final_leftovers]
        leftover_embeddings = embeddings[leftover_indices]
        
        groups_2, leftovers_2, stats_2 = _arrange_single_pass(
            final_leftovers, leftover_embeddings,
            min_cluster_size=2,          # Use smallest possible size
            min_samples=2,               # Strict
            threshold=max(0.15, threshold * 1.5), # Higher threshold safeguard
            cluster_selection_method='leaf' # 'leaf' is better for micro-clusters
        )
        
        # Merge Results
        # Handle naming collisions
        for name, items in groups_2.items():
            final_name = name
            counter = 2
            while final_name in final_groups:
                final_name = f"{name} {counter}"
                counter += 1
            final_groups[final_name] = items
            
        final_leftovers = leftovers_2

    # Consolidate Stats
    full_stats = {
        "pass_1": stats_1,
        "pass_2": stats_2
    } if return_stats else None

    if return_stats:
        return final_groups, final_leftovers, full_stats
    else:
        return final_groups, final_leftovers
