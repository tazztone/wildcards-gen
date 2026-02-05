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
from typing import List, Dict, Tuple, Optional, Any
import functools
import hashlib
import sqlite3
import pickle

from .wordnet import get_primary_synset, get_synset_name, is_abstract_category, get_synset_wnid
from .linter import check_dependencies, load_embedding_model, compute_list_embeddings, get_hdbscan_clusters
from .config import config

logger = logging.getLogger(__name__)

# Persistent Cache Config
DB_PATH = config.db_path
_MEM_CACHE = {} # LRU/Process-local cache

def _init_db():
    """Initialize SQLite database for embedding cache."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    hash TEXT PRIMARY KEY,
                    vector BLOB
                )
            """)
    except Exception as e:
        logger.warning(f"Failed to init embedding DB at {DB_PATH}: {e}")

def get_cached_embeddings(model, terms: List[str]):
    """Get embeddings with persistent SQLite caching + memory fallback."""
    # Create valid hashable key
    key_str = "|".join(sorted(terms))
    key_hash = hashlib.md5(key_str.encode('utf-8')).hexdigest()
    
    # 1. Memory Hit
    if key_hash in _MEM_CACHE:
        return _MEM_CACHE[key_hash]
        
    # 2. DB Hit
    embeddings = None
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT vector FROM embeddings WHERE hash = ?", (key_hash,))
            row = cursor.fetchone()
            if row:
                embeddings = pickle.loads(row[0])
    except Exception as e:
        logger.debug(f"DB Read failed: {e}")
        
    if embeddings is not None:
        _MEM_CACHE[key_hash] = embeddings
        return embeddings

    # 3. Compute
    embeddings = compute_list_embeddings(model, terms)
    
    # 4. Store
    _MEM_CACHE[key_hash] = embeddings
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO embeddings (hash, vector) VALUES (?, ?)",
                (key_hash, pickle.dumps(embeddings))
            )
    except Exception as e:
        logger.warning(f"DB Write failed: {e}")
        
    return embeddings

# Initialize DB on import (safe for concurrency as it's just CREATE TABLE IF NOT EXISTS)
_init_db()

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


def _generate_descriptive_name(
    lca_name: Optional[str], 
    cluster_embeddings: np.ndarray, 
    cluster_terms: List[str]
) -> Tuple[str, Dict[str, Any]]:
    """
    Generate a descriptive name using Hybrid Strategy (LCA + Medoid).
    Returns (name, metadata).
    """
    metadata = {
        "wnid": None,
        "source": "fallback",
        "examples": cluster_terms[:3]
    }
    
    # Pre-calculate medoid hypernym and term
    medoid_hypernym = get_medoid_name(cluster_embeddings, cluster_terms)
    
    # Find the actual medoid term for validation/examples
    medoid_term = None
    try:
        centroid = np.mean(cluster_embeddings, axis=0)
        distances = euclidean_distances([centroid], cluster_embeddings)
        medoid_idx = np.argmin(distances)
        medoid_term = cluster_terms[medoid_idx]
        metadata["medoid_term"] = medoid_term
    except:
        pass

    name = "Group"
    
    # Decision Logic
    # 1. LCA Validation: Ensure LCA is consistent with the Medoid
    # If LCA says "Cereal" but Medoid is "Egg", and Egg isn't a Cereal, LCA is misleading.
    # We check if LCA is a hypernym of the Medoid.
    lca_valid = False
    if lca_name and medoid_term:
        lca_synset = get_primary_synset(lca_name)
        medoid_synset = get_primary_synset(medoid_term)
        
        if lca_synset and medoid_synset:
            # Check if lca_synset is a hypernym of medoid_synset
            # set(medoid.closure(hypernyms)) contains lca?
            # Using common_hypernyms is faster than full closure check if we just check one?
            # Or just: lca_synset in list(medoid_synset.closure(lambda s: s.hypernyms()))
            # Optimization: check lowest common hypernym of (LCA, Medoid) == LCA
            lcas = medoid_synset.lowest_common_hypernyms(lca_synset)
            if lcas and lcas[0] == lca_synset:
                lca_valid = True
            elif lca_name.lower() == medoid_term.lower():
                lca_valid = True
                
    if lca_name and (not medoid_term or lca_valid):
        name = lca_name
        metadata["source"] = "lca"
        s = get_primary_synset(lca_name)
        if s:
            metadata["wnid"] = get_synset_wnid(s)
            
    elif medoid_hypernym:
        name = medoid_hypernym
        metadata["source"] = "medoid_hypernym"
        s = get_primary_synset(medoid_hypernym)
        if s:
            metadata["wnid"] = get_synset_wnid(s)
    else:
        # Fallback: Try TF-IDF
        # (Same logic as before...)
        name = "Group"
        metadata["source"] = "fallback"

    # Hybrid Data for collision handling (passed in metadata)
    if medoid_hypernym:
         metadata["medoid_hypernym"] = medoid_hypernym

    return name, metadata





def extract_unique_keywords(cluster_terms: List[str], all_terms: List[str], top_n: int = 1) -> List[str]:
    """
    Extract top keywords that distinguish this cluster from the global set using TF-IDF.
    """
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        
        if not cluster_terms or not all_terms:
            return []
            
        # 1. Construct Corpus
        # Doc 0: The cluster
        # Doc 1: Everything else (context)
        cluster_doc = " ".join(cluster_terms)
        
        # Performance optimization: Sample context if too large? 
        # For now, full context is fine for <10k items.
        context_doc = " ".join([t for t in all_terms if t not in cluster_terms])
        
        if not context_doc: # If cluster IS everything
             return []

        corpus = [cluster_doc, context_doc]
        
        # 2. Compute TF-IDF
        vectorizer = TfidfVectorizer(stop_words='english', token_pattern=r'(?u)\b\w\w+\b')
        tfidf_matrix = vectorizer.fit_transform(corpus)
        feature_names = np.array(vectorizer.get_feature_names_out())
        
        # 3. Get scores for Cluster Doc (index 0)
        cluster_scores = tfidf_matrix[0].toarray()[0]
        
        # Sort desc
        top_indices = cluster_scores.argsort()[::-1]
        
        keywords = []
        for idx in top_indices:
            word = feature_names[idx]
            # Ensure word is actually relevant (score > 0.2)
            # AND it should appear in at least a decent portion of the cluster doc
            # to be representative, especially for "Other" naming.
            score = cluster_scores[idx]
            
            # Simple check: does it appear at least twice OR is the score very high?
            count = cluster_doc.lower().count(word.lower())
            
            if score > 0.2 and (count >= 2 or score > 0.5):
                keywords.append(word)
                if len(keywords) >= top_n:
                    break
                    
        return keywords
        
    except Exception as e:
        logger.warning(f"TF-IDF extraction failed: {e}")
        return []


def generate_contextual_label(terms: List[str], context_terms: List[str], fallback: str = "Other") -> str:
    """
    Generate a descriptive label for a group of terms using TF-IDF.
    """
    if not terms:
        return fallback
        
    try:
        keywords = extract_unique_keywords(terms, context_terms, top_n=1)
        if keywords:
            # Score check is already inside extract_unique_keywords (> 0.1)
            return f"{fallback} ({keywords[0].title()})"
    except Exception:
        pass
        
    return fallback


# UMAP Cache
# Key: (hash(embeddings), n_neighbors, min_dist, n_components)
_UMAP_CACHE = {}
_UMAP_CACHE_MAX_SIZE = 10

def _hash_array(arr: np.ndarray) -> str:
    """Create a stable hash for a numpy array."""
    # Use SHA256 of the buffer
    return hashlib.sha256(arr.tobytes()).hexdigest()

def compute_umap_embeddings(embeddings: np.ndarray, n_components: int = 5, n_neighbors: int = 15, min_dist: float = 0.1) -> np.ndarray:
    """
    Reduce embedding dimensionality using UMAP for better density-based clustering.
    Falls back to original embeddings if UMAP is missing or fails.
    """
    try:
        import umap
        
        # UMAP needs enough neighbors. Default is 15.
        n_samples = embeddings.shape[0]
        if n_samples < 16:
            return embeddings

        # Check Cache
        arr_hash = _hash_array(embeddings)
        cache_key = (arr_hash, n_neighbors, float(min_dist), n_components)
        
        if cache_key in _UMAP_CACHE:
            logger.debug(f"UMAP cache hit for {n_samples} items")
            return _UMAP_CACHE[cache_key]

        # 5 components is a sweet spot for HDBSCAN (dense but not too high-dim)
        reducer = umap.UMAP(
            n_neighbors=n_neighbors, 
            n_components=n_components, 
            min_dist=min_dist, 
            metric='cosine',
            random_state=42, # Try to keep it somewhat deterministic
            n_jobs=1
        )
        result = reducer.fit_transform(embeddings)
        
        # Update Cache (LRU-style eviction not strictly implemented, just simple cap)
        if len(_UMAP_CACHE) >= _UMAP_CACHE_MAX_SIZE:
            # Remove oldest (insertion order in Python 3.7+ dicts)
            _UMAP_CACHE.pop(next(iter(_UMAP_CACHE)))
            
        _UMAP_CACHE[cache_key] = result
        return result

    except ImportError:
        logger.debug("umap-learn not installed. Skipping dimensionality reduction.")
        return embeddings
    except Exception as e:
        logger.warning(f"UMAP reduction failed: {e}. Using raw embeddings.")
        return embeddings

    except ImportError:
        logger.debug("umap-learn not installed. Skipping dimensionality reduction.")
        return embeddings
    except Exception as e:
        logger.warning(f"UMAP reduction failed: {e}. Using raw embeddings.")
        return embeddings





def _arrange_single_pass(
    terms: List[str],
    embeddings: np.ndarray,
    min_cluster_size: int,
    threshold: float,
    cluster_selection_method: str = 'eom',
    min_samples: Optional[int] = None,
    **kwargs
) -> Tuple[Dict[str, List[str]], List[str], Dict, Dict[str, Dict]]:

    """
    Internal Helper: Run a single pass of HDBSCAN clustering.
    Returns: (groups, leftovers, stats, group_metadata)
    """
    import hdbscan
    
    # Defaults
    if min_samples is None:
        min_samples = min_cluster_size

    # Extract UMAP params from kwargs or set defaults
    umap_n_neighbors = kwargs.get('umap_n_neighbors', 15)
    umap_min_dist = kwargs.get('umap_min_dist', 0.1)
    umap_n_components = kwargs.get('umap_n_components', 5)
        
    stats = {
        "n_clusters_found": 0,
        "n_clusters_rejected": 0,
        "noise_ratio": 0.0,
        "details": []
    }
    
    group_metadata = {}
        
    if len(terms) < min_cluster_size + 1:
        return {}, terms, stats, {}

    # Run HDBSCAN
    try:
        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=min_cluster_size,
            min_samples=min_samples,
            cluster_selection_epsilon=0.0,
            metric='euclidean', # We use euclidean on UMAP or raw embeddings
            cluster_selection_method=cluster_selection_method,
            prediction_data=True
        )
        # Reduce dimensionality first using UMAP if available
        # This creates a denser manifold for HDBSCAN to find clusters in
        clustering_data = compute_umap_embeddings(
             embeddings, 
             n_components=umap_n_components,
             n_neighbors=umap_n_neighbors,
             min_dist=umap_min_dist
        )
        
        clusterer.fit(clustering_data)
        
        labels = clusterer.labels_
        probabilities = clusterer.probabilities_

    except Exception as e:
        logger.warning(f"HDBSCAN error: {e}")
        return {}, terms, stats, {}

    # Process clusters
    clusters: Dict[int, List[int]] = {}
    for idx, label in enumerate(labels):
        if label != -1:
            if label not in clusters: clusters[label] = []
            clusters[label].append(idx)
            
    # Stats
    noise_count = list(labels).count(-1)
    if len(labels) > 0:
        stats["noise_ratio"] = noise_count / len(labels)
    else:
        stats["noise_ratio"] = 0.0
        
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
        lca_name = get_lca_name(cluster_items)
        cluster_embs = embeddings[indices]
        
        base_name, meta = _generate_descriptive_name(lca_name, cluster_embs, cluster_items)
        
        # Collision Handling (Hybrid Naming)
        name = base_name
        
        # If name exists or is "Group", try to enhance it
        if name in named_groups or name == "Group":
            # Hybrid: Name + (Medoid Term) or TF-IDF
            
            suffix = ""
            
            # 1. Try TF-IDF if name is generic "Group"
            if name == "Group":
                # We need context. Use leftovers + other clusters as context?
                # Or just all other terms in this pass.
                other_terms_in_pass = [t for t in terms if t not in cluster_items]
                keywords = extract_unique_keywords(cluster_items, other_terms_in_pass, top_n=1)
                if keywords:
                    suffix = keywords[0].title()
                    meta["tfidf_keyword"] = suffix
            
            # 2. If TF-IDF failed or not used, try Medoid
            if not suffix:
                medoid_term = meta.get("medoid_term", "")
                if medoid_term and medoid_term != name:
                    clean_medoid = re.sub(r'\([^)]*\)', '', medoid_term).strip()
                    if len(clean_medoid.split()) <= 2:
                        suffix = clean_medoid

            # Apply Suffix
            if suffix:
                # If we have a suffix, use it.
                # E.g. "Group (Spotted)" or "Canine (Retriever)"
                if name == "Group":
                     name = f"Group ({suffix})"
                else:
                     name = f"{base_name} ({suffix})"
                meta["is_hybrid"] = True
                
        # Final unique check with counters if Hybrid failed or collided too

        original_name = name
        counter = 2
        while name in named_groups:
            name = f"{original_name} {counter}"
            counter += 1
            
        named_groups[name] = sorted(cluster_items)
        group_metadata[name] = meta
        used_indices.update(indices)
        
    leftovers = [t for i, t in enumerate(terms) if i not in used_indices]
    return named_groups, sorted(leftovers), stats, group_metadata


def arrange_list(
    terms: List[str], 
    model_name: str = "minilm", 
    threshold: float = 0.15, 
    min_cluster_size: int = 5,
    cluster_selection_method: str = 'eom',
    return_stats: bool = False,
    return_metadata: bool = False,
    **kwargs
) -> Tuple[Dict[str, List[str]], List[str], Optional[Dict], Optional[Dict[str, Dict]]]:
    """
    Arrange a flat list into semantic sub-groups using Multi-Pass Clustering.
    If return_metadata is True, returns (groups, leftovers, stats, metadata).
    Otherwise returns standard (groups, leftovers) or (..., stats).
    """
    if not terms or len(terms) < 3:
        if return_stats:
            return ({}, terms, {}, {}) if return_metadata else ({}, terms, {})
        return ({}, terms, {}) if return_metadata else ({}, terms)
        
    if not check_dependencies():
        if return_stats:
            return ({}, terms, {"error": "missing_dependencies"}, {}) if return_metadata else ({}, terms, {"error": "missing_dependencies"})
        return ({}, terms, {}) if return_metadata else ({}, terms)

    # 1. Embeddings (Computed Once)
    model = load_embedding_model(model_name)
    normalized = [normalize_term(t) for t in terms]
    embeddings = get_cached_embeddings(model, normalized)
    
    if len(embeddings) == 0:
        if return_stats:
            return ({}, terms, {"error": "no_embeddings"}, {}) if return_metadata else ({}, terms, {"error": "no_embeddings"})
        return ({}, terms, {}) if return_metadata else ({}, terms)

    # --- PASS 1: Main Configured Pass ---
    groups_1, leftovers_1, stats_1, meta_1 = _arrange_single_pass(
        terms, embeddings, 
        min_cluster_size=min_cluster_size, 
        threshold=threshold,
        cluster_selection_method=cluster_selection_method,
        **kwargs
    )
    
    final_groups = groups_1
    final_leftovers = leftovers_1
    final_metadata = meta_1
    
    # --- PASS 2: "Cleanup" on Leftovers ---
    # Only if leftovers are substantial to avoid fragmented noise
    # and if the user isn't already using strict settings (min_size=2)
    stats_2 = None
    if len(final_leftovers) > 20 and min_cluster_size > 2:
        
        # Determine indices of leftovers in original list to slice embeddings
        leftover_indices = [i for i, t in enumerate(terms) if t in final_leftovers]
        leftover_embeddings = embeddings[leftover_indices]
        
        
        groups_2, leftovers_2, stats_2, meta_2 = _arrange_single_pass(
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
            
            # Merge Metadata
            if name in meta_2:
                final_metadata[final_name] = meta_2[name]
            
        final_leftovers = leftovers_2

    # Consolidate Stats
    full_stats = {
        "pass_1": stats_1,
        "pass_2": stats_2
    } if return_stats else None

    # Build return tuple based on flags
    result = [final_groups, final_leftovers]
    if return_stats:
        result.append(full_stats)
    if return_metadata:
        result.append(final_metadata)
        
    return tuple(result)


def arrange_hierarchy(
    terms: List[str],
    max_depth: int = 2,
    current_depth: int = 0,
    max_leaf_size: int = 50,
    **kwargs
) -> Any:
    """
    Recursive arrangement.
    Returns a structure (dict or list) suitable for direct YAML dump.
    """
    # Base case: Leaf is small enough
    if len(terms) <= max_leaf_size or current_depth >= max_depth:
        return sorted(terms)
        
    # Attempt to cluster
    # Sanitize kwargs to avoid duplicate values for control flags (popped if present)
    kwargs.pop('return_stats', None)
    kwargs.pop('return_metadata', None)
    
    groups, leftovers = arrange_list(terms, return_stats=False, return_metadata=False, **kwargs)
    
    # If clustering failed to find meaningful structure (all leftovers or 1 group), return flat
    if not groups or (len(groups) == 1 and not leftovers):
        return sorted(terms)
        
    # Build result
    result = {}
    
    # Recurse on groups
    for name, group_items in groups.items():
        # Heuristic: Only recurse if the group is still huge
        if len(group_items) > max_leaf_size:
            result[name] = arrange_hierarchy(
                group_items, 
                max_depth=max_depth,
                current_depth=current_depth + 1,
                max_leaf_size=max_leaf_size,
                **kwargs
            )
        else:
            result[name] = sorted(group_items)
            
    # Handle leftovers
    if leftovers:
        # Generate descriptive label for leftovers
        # Use existing group names as negative context
        context_names = list(groups.keys())
        # Also use a sample of items from groups as context?
        # For now, just using the group names might be enough to avoid "Group X" again.
        # But generate_contextual_label expects *terms*, not names.
        # Let's gather a sample of terms from the groups.
        context_terms = []
        for g_items in groups.values():
            context_terms.extend(g_items[:5]) # Sample 5 from each group
            
        label = generate_contextual_label(leftovers, context_terms, fallback="Other")
        result[label] = sorted(leftovers)
        
    return result

