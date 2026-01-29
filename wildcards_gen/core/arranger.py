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

def arrange_list(
    terms: List[str], 
    model_name: str = "minilm", 
    threshold: float = 0.1, 
    min_cluster_size: int = 5
) -> Tuple[Dict[str, List[str]], List[str]]:
    """
    Arrange a flat list into semantic sub-groups.
    
    Args:
        terms: List of strings to arrange
        model_name: Embedding model name
        threshold: Cluster Acceptance Cutoff (mean probability >= threshold)
        min_cluster_size: Min items per cluster
        
    Returns:
        (named_groups, leftovers)
        named_groups: Dict of {category_name: [terms]}
        leftovers: List of terms that didn't fit into high-quality clusters
    """
    # 1. Pre-checks
    if not terms or len(terms) < min_cluster_size * 2: # heuristic: need enough items
        return {}, terms
        
    if not check_dependencies():
        logger.warning("Semantic arrangement requested but dependencies missing.")
        return {}, terms

    # 2. Embeddings
    model = load_embedding_model(model_name)
    normalized = [normalize_term(t) for t in terms]
    embeddings = get_cached_embeddings(model, normalized)
    
    if len(embeddings) == 0:
        return {}, terms

    # 3. Clustering
    labels, probabilities = get_hdbscan_clusters(embeddings, min_cluster_size)
    
    # 4. Grouping & Validation
    clusters: Dict[int, List[int]] = {} # label -> list of indices
    
    for idx, label in enumerate(labels):
        if label != -1: # -1 is noise
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(idx)
            
    named_groups = {}
    used_indices = set()
    
    # Process valid clusters
    fallback_counter = 1
    
    # Sort clusters by size (descending) for stable naming order
    sorted_labels = sorted(clusters.keys(), key=lambda l: len(clusters[l]), reverse=True)
    
    for label in sorted_labels:
        indices = clusters[label]
        
        # Quality Check: Mean Probability
        probs = [probabilities[i] for i in indices]
        mean_prob = sum(probs) / len(probs)
        
        if mean_prob < threshold:
            continue # Dissolve weak cluster
            
        cluster_terms = [terms[i] for i in indices]
        
        # Naming
        name = get_lca_name(cluster_terms)
        
        # Fallback Naming
        if not name:
            name = f"Group {fallback_counter}"
            fallback_counter += 1
        
        # Ensure unique names (append index if conflict)
        original_name = name
        counter = 2
        while name in named_groups:
            name = f"{original_name} {counter}"
            counter += 1
            
        named_groups[name] = sorted(cluster_terms)
        used_indices.update(indices)
        
    # 5. Collect Leftovers
    leftovers = [t for i, t in enumerate(terms) if i not in used_indices]
    
    return named_groups, sorted(leftovers)
