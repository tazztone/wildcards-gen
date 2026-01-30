
import pytest
import os
from wildcards_gen.analytics.metrics import calculate_stability
from wildcards_gen.analytics.comparator import TaxonomyComparator

def test_jaccard_ari_perfect_match():
    """Test metrics with identical sets."""
    terms = {"dog", "cat", "bird"}
    labels = {"dog": "mammal", "cat": "mammal", "bird": "avian"}
    
    metrics = calculate_stability(terms, labels, terms, labels)
    
    assert metrics["jaccard_content"] == 1.0
    assert metrics["adjusted_rand_index"] == 1.0

def test_ari_renaming_robustness():
    """Test ARI ignores cluster labeling differences."""
    terms = {"dog", "cat", "bird"}
    # Run 1
    labels1 = {"dog": "mammal", "cat": "mammal", "bird": "avian"}
    # Run 2: Same groups, different names
    labels2 = {"dog": "group_A", "cat": "group_A", "bird": "group_B"}
    
    metrics = calculate_stability(terms, labels1, terms, labels2)
    
    assert metrics["adjusted_rand_index"] == 1.0

def test_structure_change():
    """Test detection of structural changes."""
    terms = {"dog", "cat", "bird"}
    # Run 1: Dog and Cat are together
    labels1 = {"dog": "mammal", "cat": "mammal", "bird": "avian"}
    # Run 2: Dog is separate from Cat
    labels2 = {"dog": "canine", "cat": "feline", "bird": "avian"}
    
    metrics = calculate_stability(terms, labels1, terms, labels2)
    
    # ARI should drop because grouping changed
    assert metrics["adjusted_rand_index"] < 1.0

def test_comparator_flattening():
    """Test that nested structure flattens correctly."""
    comp = TaxonomyComparator()
    structure = {
        "animal": {
            "mammal": ["dog", "cat"]
        },
        "vehicle": ["car"]
    }
    
    flat = comp.flatten_structure(structure)
    
    assert flat["dog"] == "animal/mammal"
    assert flat["cat"] == "animal/mammal"
    assert flat["car"] == "vehicle"
    assert len(flat) == 3
