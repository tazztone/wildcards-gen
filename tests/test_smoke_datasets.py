import pytest
from unittest.mock import MagicMock, patch
from wildcards_gen.core.datasets import openimages, tencent
from wildcards_gen.core.smart import SmartConfig

# === Open Images Smoke Tests ===

def test_openimages_smoke_execution_smart_flatten():
    """
    Execute the Smart flatten path in Open Images.
    Monkeypatch should_prune_node to FORCE flattening, ensuring arrangement branch logic runs.
    """
    # Mock data to return from load_openimages_data
    # Tuple: (hierarchy_dict, id_to_name_dict)
    mock_hierarchy = {
        "LabelName": "/m/root", 
        "Subcategory": [
            {
                "LabelName": "/m/obj1", 
                "Subcategory": [
                    {"LabelName": "/m/obj2"} # Leaf
                ]
            }
        ]
    }
    mock_id_to_name = {
        "/m/root": "Entity",
        "/m/obj1": "Object1",
        "/m/obj2": "Object2"
    }

    # Configure Mock Synset to handle formatting
    mock_synset = MagicMock()
    mock_synset.pos.return_value = "n"
    mock_synset.offset.return_value = 12345678 # Returns int for :08d formatting
    mock_synset.hypernym_paths.return_value = [[mock_synset]] # Path includes self
    
    # Patch load_openimages_data to bypass File I/O
    # Patch ensure_nltk_data to bypass NLTK loading
    # Patch WordNet lookups to return dummy synsets or None
    with patch("wildcards_gen.core.datasets.openimages.load_openimages_data", return_value=(mock_hierarchy, mock_id_to_name)), \
         patch("wildcards_gen.core.datasets.openimages.ensure_nltk_data"), \
         patch("wildcards_gen.core.datasets.openimages.get_primary_synset", return_value=mock_synset), \
         patch("wildcards_gen.core.datasets.openimages.get_synset_gloss", return_value="Dummy gloss"), \
         patch("wildcards_gen.core.datasets.openimages.should_prune_node", return_value=True), \
         patch("wildcards_gen.core.datasets.openimages.apply_semantic_arrangement") as mock_arrange:
        
        # Mock arrangement to return a dummy group
        # Returns (named_groups, leftovers)
        mock_arrange.return_value = ({"Cluster1": ["Object2"]}, [])
        
        from wildcards_gen.core.datasets.openimages import generate_openimages_hierarchy
        
        result = generate_openimages_hierarchy(
            smart=True,
            semantic_arrangement=True,
            semantic_arrangement_min_cluster=1
        )
        
        # Verify execution reached arrangement
        assert mock_arrange.called, "Arrangement should have been called"
        assert result is not None

# === Tencent Smoke Tests ===

def test_tencent_smoke_execution_smart_flatten():
    """
    Execute the Smart path in Tencent.
    Monkeypatch should_prune_node to FORCE flattening.
    """
    # Mock return for parse_hierarchy_file
    # categories: index -> {id, name, parent}
    # children_map: parent_index -> [child_indices]
    # roots: [index]
    mock_categories = {
        0: {'id': 'n00000000', 'name': 'Root', 'parent': -1},
        1: {'id': 'n11111111', 'name': 'Child', 'parent': 0},
        2: {'id': 'n22222222', 'name': 'Grandchild', 'parent': 1}
    }
    mock_children = {
        0: [1],
        1: [2]
    }
    mock_roots = [0]
    
    with patch("wildcards_gen.core.datasets.tencent.download_tencent_hierarchy"), \
         patch("wildcards_gen.core.datasets.tencent.parse_hierarchy_file", return_value=(mock_categories, mock_children, mock_roots)), \
         patch("wildcards_gen.core.datasets.tencent.ensure_nltk_data"), \
         patch("wildcards_gen.core.datasets.tencent.get_synset_from_wnid", return_value=MagicMock()), \
         patch("wildcards_gen.core.datasets.tencent.get_synset_gloss", return_value="Dummy gloss"), \
         patch("wildcards_gen.core.smart.should_prune_node", return_value=True), \
         patch("wildcards_gen.core.smart.apply_semantic_arrangement") as mock_arrange:
         
        mock_arrange.return_value = ({"GroupX": ["Grandchild"]}, [])
        
        from wildcards_gen.core.datasets.tencent import generate_tencent_hierarchy
        
        result = generate_tencent_hierarchy(
            smart=True,
            semantic_arrangement=True
        )
        
        assert mock_arrange.called
        assert result is not None
