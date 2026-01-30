
import pytest
import shutil
import logging
from wildcards_gen.core.arranger import arrange_list
from wildcards_gen.core.linter import check_dependencies

# Only run if dependencies are present
@pytest.mark.skipif(not check_dependencies(), reason="Missing ML dependencies")
def test_smoke_arrange_list():
    """Run arrange_list on a small list of terms to verify no exceptions."""
    
    terms = [
        "golden retriever", "labrador", "poodle", # Dogs
        "sedan", "coupe", "convertible",          # Cars
        "apple", "banana", "orange"               # Fruit
    ]
    
    # We expect roughly 3 groups, but exact clustering depends on model/params.
    # We just want to ensure it runs without crashing and returns basic structure.
    
    groups, leftovers, stats = arrange_list(
        terms, 
        model_name="minilm", # Use fastest model
        min_cluster_size=2,
        threshold=0.01,         # Low threshold to force acceptance
        return_stats=True
    )
    
    # Check outputs
    assert isinstance(groups, dict)
    assert isinstance(leftovers, list)
    assert isinstance(stats, dict)
    
    # Check that we didn't lose items
    total_out = sum(len(v) for v in groups.values()) + len(leftovers)
    assert total_out == len(terms)
    
    # Check stats integrity
    assert "pass_1" in stats
    assert "noise_ratio" in stats["pass_1"]
