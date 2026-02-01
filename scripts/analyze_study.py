"""
Deep Analysis Script for Tuning Studies.

Parses the output of a batch run and computes quality metrics:
- Fragmentation (Category Count)
- Orphan Rate (% of items in 'misc' or 'Other')
- Average Cluster Size
"""

import sys
import os
import yaml
import glob
from pathlib import Path
from wildcards_gen.core.structure import StructureManager

def analyze_structure(data):
    """Compute structural metrics."""
    mgr = StructureManager()
    all_terms = mgr.extract_terms(data)
    total_items = len(all_terms)
    
    categories = 0
    orphan_items = 0
    leaf_sizes = []
    
    def traverse(node, path):
        nonlocal categories, orphan_items
        if isinstance(node, dict):
            for k, v in node.items():
                is_orphan_key = k.lower() in ['misc', 'other'] or k.lower().startswith('other (')
                
                if isinstance(v, list):
                    categories += 1
                    leaf_sizes.append(len(v))
                    if is_orphan_key:
                        orphan_items += len(v)
                else:
                    traverse(v, path + [k])
    
    # Call the inner function
    traverse(data, [])
    
    avg_size = sum(leaf_sizes) / len(leaf_sizes) if leaf_sizes else 0
    orphan_rate = (orphan_items / total_items * 100) if total_items > 0 else 0
    
    return {
        "Total": total_items,
        "Cats": categories,
        "AvgSize": round(avg_size, 1),
        "Orphans": orphan_items,
        "Orphan%": round(orphan_rate, 1)
    }

def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_study.py <experiment_dir>")
        sys.exit(1)
        
    exp_dir = sys.argv[1]
    files = sorted(glob.glob(os.path.join(exp_dir, "*.yaml")))
    
    print(f"\n📊 Analyzing {len(files)} runs in {exp_dir}")
    print(f"{ 'Run Name':<55} | {'Cats':<5} | {'AvgSz':<7} | {'Orphan%':<7} | {'Total':<6}")
    print("-" * 90)
    
    mgr = StructureManager()
    
    for f in files:
        name = Path(f).stem
        if "clean" in name: continue # Skip intermediate clean files if any
        
        try:
            data = mgr.load_structure(f)
            stats = analyze_structure(data)
            
            print(f"{name:<55} | {stats['Cats']:<5} | {stats['AvgSize']:<7} | {stats['Orphan%']:<7} | {stats['Total']:<6}")
        except Exception as e:
            print(f"{name:<55} | ERROR: {e}")

if __name__ == "__main__":
    main()
