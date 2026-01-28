"""
Dataset Analysis Module.

Computes structural statistics (depth, branching factor, leaf density)
and suggests optimal 'Smart Mode' pruning thresholds.
"""

from typing import Any, Dict, List, Union
from ruamel.yaml.comments import CommentedMap, CommentedSeq

class DatasetStats:
    def __init__(self):
        self.max_depth = 0
        self.total_nodes = 0
        self.total_leaves = 0
        self.leaf_lists = 0
        self.branching_factors = []
        self.leaf_sizes = []

    def to_dict(self):
        avg_branching = sum(self.branching_factors) / len(self.branching_factors) if self.branching_factors else 0
        avg_leaf_size = sum(self.leaf_sizes) / len(self.leaf_sizes) if self.leaf_sizes else 0
        
        return {
            "max_depth": self.max_depth,
            "total_nodes": self.total_nodes,
            "total_leaves": self.total_leaves,
            "avg_branching": round(avg_branching, 2),
            "avg_leaf_size": round(avg_leaf_size, 2)
        }

def compute_dataset_stats(data: Union[Dict, List, CommentedMap, CommentedSeq]) -> DatasetStats:
    """
    Traverse the dataset structure and compute statistics.
    Assumes a recursive dictionary structure where leaves are lists of strings.
    """
    stats = DatasetStats()
    
    def traverse(node: Any, current_depth: int):
        stats.total_nodes += 1
        stats.max_depth = max(stats.max_depth, current_depth)
        
        if isinstance(node, (dict, CommentedMap)):
            # It's a category
            children = list(node.values())
            child_count = len(children)
            if child_count > 0:
                stats.branching_factors.append(child_count)
            
            for key, value in node.items():
                traverse(value, current_depth + 1)
                
        elif isinstance(node, (list, CommentedSeq)):
            # It's a leaf list
            count = len(node)
            stats.total_leaves += count
            stats.leaf_lists += 1
            stats.leaf_sizes.append(count)
            
    traverse(data, 0)
    return stats

def suggest_thresholds(stats: DatasetStats) -> Dict[str, int]:
    """
    Algorithmically determine smart pruning thresholds based on stats.
    
    Rules:
    - min_depth: Keep fundamental categories (shallow).
    - min_hyponyms: Scale with dataset size to avoid clutter.
    - min_leaf: Ensure leaf lists have enough variety.
    """
    s = stats.to_dict()
    
    # Rule 1: Min Depth
    # If tree is very deep (e.g. 12), we can be aggressive and start pruning at 4.
    # If shallow (e.g. 5), we should preserve more structure.
    suggested_depth = min(s['max_depth'] - 2, 4)
    suggested_depth = max(2, suggested_depth) # Floor at 2
    
    # Rule 2: Min Hyponyms (Flattening Threshold)
    # Higher total leaves = need more aggressive flattening to reduce file size.
    # Base: 50. Add 1 for every 100 leaves.
    suggested_hyponyms = max(50, s['total_leaves'] // 100)
    
    # Rule 3: Min Leaf Size
    # Tie to average branching. Denser trees can support larger leaf lists.
    # Base: 3.
    suggested_leaf = max(3, int(s['avg_branching'] // 5))
    
    return {
        "min_depth": suggested_depth,
        "min_hyponyms": suggested_hyponyms,
        "min_leaf_size": suggested_leaf
    }

def print_analysis_report(stats: DatasetStats, suggestions: Dict[str, int]):
    """Print a formatted report to console."""
    s = stats.to_dict()
    
    print("\n📊 Dataset Analysis Report")
    print("=" * 30)
    print(f"Max Depth:       {s['max_depth']}")
    print(f"Total Leaves:    {s['total_leaves']}")
    print(f"Avg Branching:   {s['avg_branching']}")
    print(f"Avg Leaf Size:   {s['avg_leaf_size']}")
    print("-" * 30)
    print("💡 Suggested Smart Thresholds:")
    print(f"  --min-depth     {suggestions['min_depth']}")
    print(f"  --min-hyponyms  {suggestions['min_hyponyms']}")
    print(f"  --min-leaf      {suggestions['min_leaf_size']}")
    print("=" * 30)
    print("\nTo apply these suggestions, run with:")
    print(f"  --smart --min-depth {suggestions['min_depth']} --min-hyponyms {suggestions['min_hyponyms']} --min-leaf {suggestions['min_leaf_size']}")
