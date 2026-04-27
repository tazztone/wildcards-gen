import pytest
import sys
from unittest.mock import MagicMock, patch
from ruamel.yaml.comments import CommentedMap
from wildcards_gen.core.datasets.imagenet import generate_imagenet_tree
from wildcards_gen.core.wordnet import get_primary_synset

def test_integration_pipeline_shaping(mock_wn, sample_hierarchy, mock_arranger_deps):
    """
    Test that generate_imagenet_tree:
    1. Generates a structure
    2. Respects min_leaf_size (merging orphans)
    3. Preserves CommentedMap type
    """

    # Configure mock to return valid clusters (15 items in one cluster)
    mock_arranger_deps["clusterer"].labels_ = [0]*15
    mock_arranger_deps["clusterer"].probabilities_ = [1.0]*15

    # We also need to mock embeddings related stuff to avoid needing sentence-transformers
    # The arranger logic calls load_embedding_model and get_cached_embeddings

    # We need a dummy embeddings array that matches the length of terms (15 items for vehicle)
    # However, the code generates embeddings for *children*.
    # For 'vehicle', there are 15 children.

    import numpy as np
    dummy_embeddings = np.zeros((15, 10)) # 15 items, 10 dims

    with patch('wildcards_gen.core.linter.check_dependencies', return_value=True), \
            patch("wildcards_gen.core.datasets.imagenet.ensure_nltk_data"), \
            patch("wildcards_gen.core.datasets.imagenet.load_imagenet_1k_wnids", return_value=None), \
            patch("wildcards_gen.core.builder.apply_semantic_arrangement") as mock_arrange:
        
        # Mock arrangement to return everything as leftovers
        # This forces the orphans path which uses min_leaf_size
        mock_arrange.side_effect = lambda items, *args, **kwargs: ({}, items)

        node = generate_imagenet_tree(
            root_synset_str="entity.n.01",
            max_depth=4, # Give it enough depth
            with_glosses=False
        )
        
        from wildcards_gen.core.builder import HierarchyBuilder
        from wildcards_gen.core.smart import SmartConfig
        config_obj = SmartConfig(
            enabled=True,
            min_depth=1,
            min_leaf_size=5,
            merge_orphans=True,
            semantic_arrangement=True, # Trigger arranger
            semantic_arrangement_min_cluster=2
        )
        builder = HierarchyBuilder(config_obj)
        result = builder.build(node)
    
    # Verify Type
    assert isinstance(result, CommentedMap)
    
    # Debug print
    from ruamel.yaml import YAML
    yaml = YAML()
    print("\n--- Result Structure ---")
    yaml.dump(result, sys.stdout)

    # Verify Content
    assert "Entity" in result
    entity = result["Entity"]
    assert "Animal" in entity
    assert "Vehicle" in entity
    
    # Animal check (should have orphans merged into misc/Other)
    assert isinstance(entity["Animal"], list)
    assert len(entity["Animal"]) >= 5
    assert "poodle" in entity["Animal"]
    
    # Vehicle check (15 items, clustered)
    assert isinstance(entity["Vehicle"], list)
    assert len(entity["Vehicle"]) == 15
    assert "vehicle 0" in entity["Vehicle"]
