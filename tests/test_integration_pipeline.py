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

    with patch('wildcards_gen.core.arranger.check_dependencies', return_value=True), \
            patch("wildcards_gen.core.datasets.imagenet.ensure_nltk_data"), \
            patch("wildcards_gen.core.datasets.imagenet.load_imagenet_1k_wnids", return_value=None), \
            patch("wildcards_gen.core.arranger.load_embedding_model"), \
            patch("wildcards_gen.core.arranger.get_cached_embeddings", return_value=dummy_embeddings):

        result = generate_imagenet_tree(
            root_synset_str="entity.n.01",
            smart=True,
            min_significance_depth=1, 
            min_leaf_size=5,
            merge_orphans=True,
            with_glosses=False
        )
    
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
