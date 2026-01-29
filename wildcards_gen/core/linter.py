"""
Semantic Linter Module.

Uses embedding models (Qwen3, MPNet, MiniLM) and HDBSCAN* to detect
semantic outliers in wildcard lists.
"""

import logging
from typing import List, Tuple, Dict, Any
import numpy as np

logger = logging.getLogger(__name__)

# Model registry
MODELS = {
    "qwen3": "Qwen/Qwen3-Embedding-0.6B",
    "mpnet": "sentence-transformers/all-mpnet-base-v2",
    "minilm": "sentence-transformers/all-MiniLM-L12-v2",
}

def check_dependencies():
    """Ensure optional dependencies are installed."""
    try:
        import sentence_transformers
        import hdbscan
        return True
    except ImportError:
        return False

def load_embedding_model(model_name: str = "qwen3"):
    """Load embedding model by short name."""
    from sentence_transformers import SentenceTransformer
    
    model_id = MODELS.get(model_name, MODELS["qwen3"])
    logger.info(f"Loading embedding model: {model_id}...")
    return SentenceTransformer(model_id, trust_remote_code=True)

def compute_list_embeddings(model, terms: List[str]):
    """Encode terms using selected embedding model."""
    if not terms:
        return np.array([])
    return model.encode(terms, show_progress_bar=False)

def get_hdbscan_clusters(embeddings: np.ndarray, min_cluster_size: int = 2) -> Tuple[np.ndarray, np.ndarray]:
    """
    Run HDBSCAN on embeddings.
    Returns:
        (labels, probabilities)
        labels: Cluster labels (-1 is noise)
        probabilities: Membership probabilities
    """
    import hdbscan
    
    if len(embeddings) < min_cluster_size + 1:
        # Not enough data to cluster meaningfully
        return np.array([-1] * len(embeddings)), np.array([0.0] * len(embeddings))

    try:
        # min_cluster_size=2 allows detecting even small anomalies in small lists
        clusterer = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size, gen_min_span_tree=True)
        clusterer.fit(embeddings)
        return clusterer.labels_, clusterer.probabilities_
    except Exception as e:
        logger.warning(f"HDBSCAN failed: {e}")
        return np.array([-1] * len(embeddings)), np.array([0.0] * len(embeddings))


def detect_outliers_hdbscan(embeddings: np.ndarray, threshold: float = 0.1) -> List[Tuple[int, float]]:
    """
    HDBSCAN* outlier scoring.
    Returns list of (index, score) for terms with score > threshold.
    """
    import hdbscan
    
    if len(embeddings) < 3:
        return []

    try:
        clusterer = hdbscan.HDBSCAN(min_cluster_size=2, gen_min_span_tree=True)
        clusterer.fit(embeddings)
        
        # outlier_scores_ returns values where higher is more anomalous
        scores = clusterer.outlier_scores_
        
        # Filter by threshold
        outliers = [(i, float(s)) for i, s in enumerate(scores) if s > threshold]
        
        # Sort by score descending (most anomalous first)
        return sorted(outliers, key=lambda x: -x[1])
    except Exception as e:
        logger.warning(f"HDBSCAN failed: {e}")
        return []

def lint_file(file_path: str, model_name: str, threshold: float) -> Dict[str, Any]:
    """
    Main entry point: Lint a YAML skeleton file.
    """
    from wildcards_gen.core.structure import StructureManager
    
    if not check_dependencies():
        raise ImportError("Missing dependencies. Install with: pip install wildcards-gen[lint] (or uv pip install 'wildcards-gen[lint]')")

    mgr = StructureManager()
    structure = mgr.load_structure(file_path)
    if not structure:
        raise ValueError(f"Could not load structure from {file_path}")

    # Initialize model
    model = load_embedding_model(model_name)
    
    report = {
        "file": file_path,
        "model": MODELS.get(model_name, model_name),
        "threshold": threshold,
        "issues": []
    }
    
    # Traverse and check leaf lists
    def traverse(node, path):
        if isinstance(node, dict):
            for k, v in node.items():
                traverse(v, path + [k])
        elif isinstance(node, list):
            # It's a leaf list
            if len(node) < 3:
                return # Too small to check
            
            embeddings = compute_list_embeddings(model, node)
            outliers = detect_outliers_hdbscan(embeddings, threshold)
            
            if outliers:
                issue = {
                    "path": "/".join(path),
                    "outliers": []
                }
                for idx, score in outliers:
                    issue["outliers"].append({
                        "term": node[idx],
                        "score": round(score, 3)
                    })
                report["issues"].append(issue)

    traverse(structure, [])
    return report, structure

def clean_structure(structure: Dict[str, Any], report: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove identified outliers from the structure.
    """
    import copy
    clean_data = copy.deepcopy(structure)
    
    # Map paths to outliers for quick lookup
    path_to_outliers = {issue['path']: set(o['term'] for o in issue['outliers']) for issue in report['issues']}
    
    def traverse_and_clean(node, path_parts):
        path = "/".join(path_parts)
        if isinstance(node, dict):
            for k in list(node.keys()):
                traverse_and_clean(node[k], path_parts + [k])
        elif isinstance(node, list):
            if path in path_to_outliers:
                outliers = path_to_outliers[path]
                # Filter out the terms that are considered outliers
                new_list = [term for term in node if term not in outliers]
                node.clear()
                node.extend(new_list)
                
    traverse_and_clean(clean_data, [])
    return clean_data

def clean_list(terms: List[str], model: Any, threshold: float = 0.1) -> Tuple[List[str], List[str]]:
    """
    Clean a single list of terms using the embedding model.
    Returns (cleaned_terms, outliers).
    """
    if len(terms) < 3:
        return terms, []

    embeddings = compute_list_embeddings(model, terms)
    outlier_indices_scores = detect_outliers_hdbscan(embeddings, threshold)
    
    if not outlier_indices_scores:
        return terms, []
    
    outlier_indices = {idx for idx, _ in outlier_indices_scores}
    cleaned = [term for i, term in enumerate(terms) if i not in outlier_indices]
    outliers = [term for i, term in enumerate(terms) if i in outlier_indices]
    
    return cleaned, outliers

def print_lint_report(report: Dict[str, Any], output_format: str = 'markdown'):
    """Print the lint report to console."""
    if output_format == 'json':
        import json
        print(json.dumps(report, indent=2))
        return

    print(f"\n🧹 Semantic Lint Report: {report['file']}")
    print(f"Model: {report['model']} | Threshold: {report['threshold']}")
    print("=" * 60)
    
    if not report['issues']:
        print("✅ No semantic outliers detected.")
        return

    for issue in report['issues']:
        print(f"\n📂 {issue['path']}")
        print(f"   {'Term':<40} | {'Score':<10}")
        print(f"   {'-'*40} | {'-'*10}")
        for out in issue['outliers']:
            print(f"   {out['term']:<40} | {out['score']:<10}")
            
    print("=" * 60)
