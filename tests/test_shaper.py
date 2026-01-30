
import pytest
from wildcards_gen.core.shaper import ConstraintShaper

def test_merge_orphans():
    """Test merging small list nodes into 'Other'."""
    tree = {
        "GroupA": ["a1", "a2", "a3"], # 3 items
        "GroupB": ["b1"] * 20,        # 20 items
        "GroupC": ["c1", "c2"]        # 2 items
    }
    
    # Min size 5 -> A and C go to Other
    shaper = ConstraintShaper(tree)
    result = shaper.shape(min_leaf_size=5, flatten_singles=False)
    
    assert "GroupB" in result
    assert "GroupA" not in result
    assert "GroupC" not in result
    assert "Other" in result
    assert len(result["Other"]) == 5 # 3 + 2

def test_merge_orphans_recursive():
    """Test merging happens deep in the tree."""
    tree = {
        "Top": {
            "Sub1": ["x"] * 2, # Small
            "Sub2": ["y"] * 10
        }
    }
    shaper = ConstraintShaper(tree)
    result = shaper.shape(min_leaf_size=5, flatten_singles=False)
    
    assert "Other" in result["Top"]
    assert "Sub1" not in result["Top"]
    assert len(result["Top"]["Other"]) == 2

def test_flatten_singles():
    """Test removing intermediate single-child dicts."""
    tree = {
        "Level1": {
            "Level2": {
                "Level3": ["items"]
            }
        }
    }
    # Level1 has 1 child (Level2). 
    # Level2 has 1 child (Level3).
    # Level3 has 1 child (list) -> STOP, don't flatten leaf container.
    
    shaper = ConstraintShaper(tree)
    result = shaper.shape(flatten_singles=True, min_leaf_size=0)
    
    # Expectation: Level1 -> Level2 (dict) -> promotes Level2?
    # Result should be just {Level3: ...} ??
    # Wait, flatten_singles returns the VALUE.
    # Level2 returns {Level3: ...}
    # Level1 returns {Level3: ...}
    
    # The root wrapper remains? 
    # shaper.shape calls _flatten_singles(tree)
    # tree is dict len 1. -> returns child val ({Level2...})
    # then recurse...
    
    # Wait, if I pass a dict {A: {B: ...}}, it returns {B: ...}.
    # So top key "A" is lost. 
    # Usually we pass the *Content* of the YAML file.
    
    assert "Level3" in result
    assert result["Level3"] == ["items"]
    assert "Level1" not in result
    assert "Level2" not in result

def test_flatten_singles_leaf_protection():
    """Ensure {Category: [list]} is NOT flattened to [list]."""
    tree = {
        "Category": ["item1", "item2"]
    }
    shaper = ConstraintShaper(tree)
    result = shaper.shape(flatten_singles=True, min_leaf_size=0)
    
    # Should stay as dict
    assert isinstance(result, dict)
    assert "Category" in result
    assert isinstance(result["Category"], list)
