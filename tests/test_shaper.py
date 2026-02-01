
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
    
    assert "Groupb" in result
    assert "Groupa" not in result
    assert "Groupc" not in result
    # Find the key that was used for merged items (may be "Other" or "Other (Keyword)")
    other_key = next((k for k in result.keys() if k.startswith("Other")), None)
    assert other_key is not None
    # Ensure items were moved
    assert len(result[other_key]) == 5 # 3 + 2

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
    
    other_key = next((k for k in result["Top"].keys() if k.startswith("Other")), None)
    assert other_key is not None
    assert "Sub1" not in result["Top"]
    # x * 2 becomes one x due to deduplication during casing normalization
    assert len(result["Top"][other_key]) == 1

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
    result = shaper.shape(flatten_singles=True, min_leaf_size=0, preserve_roots=False)
    
    # Expectation: Level1 -> Level2 (dict) -> promotes Level2?
    # Result should be just {Level3: ...} ??
    # Wait, flatten_singles returns the VALUE.
    # Level2 returns {Level3: ...}
    # Level1 returns {Level3: ...}
    
    assert "Level3" in result
    assert isinstance(result["Level3"], list)
    assert "items" in result["Level3"]
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

def test_prune_tautologies():
    """Test removing nodes where parent name == child name."""
    from wildcards_gen.core.shaper import ConstraintShaper
    
    # Simple tautology
    tree = {"Fish": {"Fish": ["salmon", "trout"]}}
    shaper = ConstraintShaper(tree)
    result = shaper.shape(min_leaf_size=0, flatten_singles=False)
    
    assert result == {"Fish": ["salmon", "trout"]}

    # Case insensitive and deep
    tree = {
        "ANIMAL": {
            "Chordate": {
                "chordate": ["human", "dog"]
            }
        }
    }
    shaper = ConstraintShaper(tree)
    # preserve_roots=True (default) keeps ANIMAL
    result = shaper.shape(min_leaf_size=0, flatten_singles=False)
    assert "Animal" in result
    assert result["Animal"] == {"Chordate": ["dog", "human"]}

def test_contextual_other(mocker):
    """Test that 'Other' blocks get contextual names if possible."""
    # We mock generate_contextual_label to avoid sklearn dependency in tests
    mocker.patch("wildcards_gen.core.arranger.generate_contextual_label", return_value="Other (Fruit)")
    
    from wildcards_gen.core.shaper import ConstraintShaper
    
    tree = {
        "Apple": ["granny smith"],
        "Banana": ["cavendish"],
        "Meat": ["beef", "chicken", "pork", "lamb", "turkey"] # Regular size
    }
    
    shaper = ConstraintShaper(tree)
    # min_leaf_size=5 -> Apple and Banana (size 1) should merge
    result = shaper.shape(min_leaf_size=5, flatten_singles=False)
    
    assert "Meat" in result
    assert result["Other (Fruit)"] == ["cavendish", "granny smith"]

def test_normalize_casing():
    """Test Title Case categories and lowercase items."""
    from wildcards_gen.core.shaper import ConstraintShaper
    
    tree = {
        "FOOD": {
            "fruit": ["Apple", "BANANA"]
        },
        "vegetable": ["CARROT"]
    }
    
    shaper = ConstraintShaper(tree)
    result = shaper.shape(min_leaf_size=0, flatten_singles=False)
    
    # Categories should be Title Case
    assert "Food" in result
    assert "Fruit" in result["Food"]
    assert "Vegetable" in result
    
    # Leaf items should be lowercase and sorted
    assert result["Food"]["Fruit"] == ["apple", "banana"]
    assert result["Vegetable"] == ["carrot"]
