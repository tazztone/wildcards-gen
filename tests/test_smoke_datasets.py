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
    
    # Configure lemmas for get_synset_name
    mock_lemma = MagicMock()
    mock_lemma.name.return_value = "lemma_name"
    mock_synset.lemmas.return_value = [mock_lemma]
    
    # Patch load_openimages_data to bypass File I/O
    # Patch ensure_nltk_data to bypass NLTK loading
    # Patch WordNet lookups to return dummy synsets or None
    with patch("wildcards_gen.core.datasets.openimages.load_openimages_data", return_value=(mock_hierarchy, mock_id_to_name)), \
         patch("wildcards_gen.core.datasets.openimages.ensure_nltk_data"), \
         patch("wildcards_gen.core.datasets.openimages.get_primary_synset", return_value=mock_synset), \
         patch("wildcards_gen.core.datasets.openimages.get_synset_gloss", return_value="Dummy gloss"), \
         patch("wildcards_gen.core.datasets.openimages.should_prune_node", return_value=True), \
         patch("wildcards_gen.core.datasets.openimages.apply_semantic_arrangement") as mock_arrange:
        
        # Clear cache to avoid pollution from other tests
        from wildcards_gen.core.datasets import openimages
        openimages._get_cached_synset_tree.cache_clear()
        
        # Mock arrangement to return a dummy group
        # Returns (named_groups, leftovers)
        mock_arrange.return_value = ({"Cluster1": ["Object2", "Object2b"], "Cluster2": ["Object3", "Object3b"]}, [])
        
        from wildcards_gen.core.datasets.openimages import generate_openimages_hierarchy
        
        result = generate_openimages_hierarchy(
            smart=True,
            semantic_arrangement=True,
            semantic_arrangement_min_cluster=1,
            min_leaf_size=0 # Disable shaper to verify raw structure
        )
        
        # Verify execution reached arrangement
        assert mock_arrange.called, "Arrangement should have been called"
        assert result is not None
        
        # Verify outcome: The arranged cluster should be in the result structure
        def find_key(data, key):
            if isinstance(data, dict):
                if key in data: return True
                return any(find_key(v, key) for v in data.values())
            return False
            
        assert find_key(result, "Cluster1"), "Arranged cluster 'Cluster1' not found in result"

        # Verify Round-Trip (Catch "MagicMock is not serializable" bugs)
        try:
            from ruamel.yaml import YAML
            yaml = YAML()
            from io import StringIO
            stream = StringIO()
            yaml.dump(result, stream)
            assert stream.getvalue(), "YAML dump should not be empty"
        except Exception as e:
            pytest.fail(f"Result structure is not valid YAML-serializable: {e}")

def test_openimages_smoke_empty_arrangement():
    """
    Verify graceful handling when arrangement returns no groups (only leftovers).
    """
    mock_hierarchy = {"LabelName": "/m/root", "Subcategory": [{"LabelName": "/m/leaf"}]}
    mock_id_to_name = {"/m/root": "Entity", "/m/leaf": "Leaf"}
    mock_synset = MagicMock()
    mock_synset.pos.return_value = "n"
    mock_synset.offset.return_value = 11111111
    mock_synset.hypernym_paths.return_value = [[mock_synset]]

    with patch("wildcards_gen.core.datasets.openimages.load_openimages_data", return_value=(mock_hierarchy, mock_id_to_name)), \
         patch("wildcards_gen.core.datasets.openimages.ensure_nltk_data"), \
         patch("wildcards_gen.core.datasets.openimages.get_primary_synset", return_value=mock_synset), \
         patch("wildcards_gen.core.datasets.openimages.get_synset_gloss", return_value=""), \
         patch("wildcards_gen.core.datasets.openimages.should_prune_node", return_value=True), \
         patch("wildcards_gen.core.datasets.openimages.apply_semantic_arrangement") as mock_arrange:
         
        # Return empty groups, all items as leftovers
        mock_arrange.return_value = ({}, ["Leaf"])
        
        from wildcards_gen.core.datasets.openimages import generate_openimages_hierarchy
        result = generate_openimages_hierarchy(smart=True, semantic_arrangement=True)
        
        # Should not crash, and "Leaf" should be visible (likely in a flat list or 'misc' depending on implementation)
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
         
        mock_arrange.return_value = ({"GroupX": ["Grandchild", "G2"], "GroupY": ["Sibling", "S2"]}, [], {})
        
        from wildcards_gen.core.datasets.tencent import generate_tencent_hierarchy
        
        result = generate_tencent_hierarchy(
            smart=True,
            semantic_arrangement=True,
            min_leaf_size=0 # Disable shaper
        )
        
        assert mock_arrange.called
        assert result is not None
        
        # Verify outcome
        def find_key(data, key):
             if isinstance(data, dict):
                 if key in data: return True
                 return any(find_key(v, key) for v in data.values())
             return False
        assert find_key(result, "GroupX"), "Arranged group 'GroupX' not found in result"
