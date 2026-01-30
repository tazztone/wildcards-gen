"""
Stability Metrics for Taxonomy Evaluation.

This module implements metrics to compare two versions of a taxonomy.
"""

import logging
from typing import Set, List, Dict, Tuple, Any, Optional

logger = logging.getLogger(__name__)

def check_dependencies():
    """Ensure sklearn is installed."""
    try:
        import sklearn.metrics
        return True
    except ImportError:
        return False

def calculate_stability(
    terms1: Set[str], 
    labels1: Dict[str, str], 
    terms2: Set[str], 
    labels2: Dict[str, str]
) -> Dict[str, float]:
    """
    Calculate stability metrics between two taxonomy states.
    
    Args:
        terms1: Set of all terms in the first taxonomy.
        labels1: Dict mapping term -> cluster_label (path) for first taxonomy.
        terms2: Set of all terms in the second taxonomy.
        labels2: Dict mapping term -> cluster_label (path) for second taxonomy.
        
    Returns:
        Dictionary containing:
        - jaccard_content: Similarity of the term sets (content stability).
        - adjusted_rand_index: Similarity of the clustering (structural stability).
    """
    if not check_dependencies():
        raise ImportError(
             "Missing 'scikit-learn'. Install with: pip install wildcards-gen[lint]"
        )

    from sklearn.metrics import adjusted_rand_score

    # 1. Content Stability (Jaccard)
    # How many terms are preserved?
    intersection = terms1.intersection(terms2)
    union = terms1.union(terms2)
    
    jaccard = len(intersection) / len(union) if union else 1.0

    # 2. Structural Stability (ARI)
    # We can only compare clustering on the INTERSECTION of terms.
    # If the intersection is empty or too small, ARI is undefined/irrelevant.
    if len(intersection) < 2:
        ari = 1.0 if len(intersection) == len(union) else 0.0
    else:
        # Sort terms to ensure alignment
        common_terms = sorted(list(intersection))
        
        y_true = [labels1[t] for t in common_terms]
        y_pred = [labels2[t] for t in common_terms]
        
        ari = adjusted_rand_score(y_true, y_pred)

    return {
        "jaccard_content": round(jaccard, 4),
        "adjusted_rand_index": round(ari, 4),
        "common_terms_count": len(intersection),
        "union_terms_count": len(union)
    }
