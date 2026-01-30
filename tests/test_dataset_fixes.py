
import pytest
from unittest.mock import patch, MagicMock
from wildcards_gen.core.datasets import openimages, tencent
from ruamel.yaml import CommentedMap

@pytest.fixture
def mock_deps():
    with patch('wildcards_gen.core.datasets.openimages.load_openimages_data') as mock_oi_load, \
         patch('wildcards_gen.core.datasets.tencent.download_tencent_hierarchy', return_value="dummy.tsv"), \
         patch('wildcards_gen.core.datasets.tencent.parse_hierarchy_file') as mock_t_parse, \
         patch('wildcards_gen.core.datasets.openimages.ensure_nltk_data'), \
         patch('wildcards_gen.core.datasets.tencent.ensure_nltk_data'):
         
         # Mock OI data
         mock_oi_load.return_value = (None, {"/m/cat1": "Dog", "/m/cat2": "Cat"})
         
         # Mock Tencent data
         # categories, children_map, roots
         mock_t_parse.return_value = (
             {0: {'id': 'n000', 'name': 'Entity', 'parent': -1}, 
              1: {'id': 'n001', 'name': 'Animal', 'parent': 0}},
             {0: [1]},
             [0]
         )
         openimages._get_cached_synset_tree.cache_clear()
         yield
         openimages._get_cached_synset_tree.cache_clear()

def test_openimages_nested_arrangement(mock_deps):
    # Test that openimages handles nested arrangement dicts
    # Patch the source since it might be locally imported
    with patch('wildcards_gen.core.smart.apply_semantic_arrangement') as mock_arrange, \
         patch('wildcards_gen.core.datasets.openimages.get_synset_gloss', return_value="gloss"), \
         patch('wildcards_gen.core.shaper.ConstraintShaper') as MockShaper:
         
        # Mock arrangement to return a nested dict structure
        # Mock arrangement to return a nested dict structure (and leftovers)
        # e.g. "Animals" -> {"Mammals": ["Dog"], "Others": ["Cat"]}
        mock_arrange.return_value = ({"Mammals": ["Dog"], "Others": ["Cat"]}, [])
        
        # Mock Shaper to just pass through or verify it was called
        mock_shaper_instance = MagicMock()
        mock_shaper_instance.shape.side_effect = lambda **kwargs: {"Result": "Shaped"}
        MockShaper.return_value = mock_shaper_instance

        # Call generation
        # smart=True, semantic_arrangement=True
        result = openimages.generate_openimages_hierarchy(
            smart=True, 
            semantic_arrangement=True,
            bbox_only=False,
            # Force it to go into the logic
            min_leaf_size=1
        )
        
        # Verify ConstraintShaper was called
        MockShaper.assert_called()
        assert result == {"Result": "Shaped"}

def test_tencent_nested_arrangement(mock_deps):
    # Test that tencent handles nested arrangement dicts
    with patch('wildcards_gen.core.smart.apply_semantic_arrangement') as mock_arrange, \
         patch('wildcards_gen.core.datasets.tencent.get_synset_gloss', return_value="gloss"), \
         patch('wildcards_gen.core.datasets.tencent.get_synset_from_wnid'), \
         patch('wildcards_gen.core.shaper.ConstraintShaper') as MockShaper:

         
        # Mock arrangement to return a nested dict (and leftovers, metadata)
        mock_arrange.return_value = ({"SubGroup": ["Item1"], "Other": ["Item2"]}, [], {})
        
        # Mock Shaper
        mock_shaper_instance = MagicMock()
        mock_shaper_instance.shape.side_effect = lambda **kwargs: {"Result": "Shaped"}
        MockShaper.return_value = mock_shaper_instance

        # Call generation
        result = tencent.generate_tencent_hierarchy(
            smart=True, 
            semantic_arrangement=True,
            min_leaf_size=1
        )
        
        # Verify ConstraintShaper was called
        MockShaper.assert_called()
        assert result == {"Result": "Shaped"}
