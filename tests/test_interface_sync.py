import pytest
from unittest.mock import MagicMock, patch
from wildcards_gen.core.datasets import imagenet, tencent, openimages
from wildcards_gen.gui import generate_dataset_handler

@pytest.fixture
def mock_stats():
    return MagicMock()

@pytest.fixture
def base_kwargs():
    """Mock the exhaustive kwargs passed from gui.py"""
    return {
        "dataset_name": "ImageNet",
        "strategy": "Smart",
        "root": "entity.n.01",
        "depth": 4,
        "output_name": "test.yaml",
        "with_glosses": True,
        "filter_set": "none",
        "strict_filter": True,
        "blacklist_abstract": False,
        "min_depth": 4,
        "min_hyponyms": 50,
        "min_leaf": 5,
        "merge_orphans": True,
        "bbox_only": False,
        "semantic_clean": False,
        "semantic_model": "minilm",
        "semantic_threshold": 0.1,
        "semantic_arrange": False,
        "semantic_arrange_threshold": 0.1,
        "semantic_arrange_min_cluster": 5,
        "exclude_subtree": None,
        "exclude_regex": None,
        "semantic_arrange_method": "eom",
        "debug_arrangement": False,
        "umap_neighbors": 15,
        "umap_dist": 0.1,
        "min_samples": 5,
        "orphans_template": "misc",
        "fast_preview": False
    }

def test_imagenet_signature_sync(base_kwargs):
    with patch("wildcards_gen.core.datasets.imagenet.generate_imagenet_tree") as mock_gen, \
         patch("wildcards_gen.gui.save_and_preview", return_value=("path", "preview")):
        
        # Call the handler which calls the dataset function
        generate_dataset_handler(**base_kwargs)
        
        # Verify it was called and DID NOT raise TypeError
        assert mock_gen.called
        args, kwargs = mock_gen.call_args
        assert "umap_n_neighbors" in kwargs
        assert "umap_min_dist" in kwargs
        assert "hdbscan_min_samples" in kwargs

def test_tencent_signature_sync(base_kwargs):
    base_kwargs["dataset_name"] = "Tencent ML-Images"
    with patch("wildcards_gen.core.datasets.tencent.generate_tencent_hierarchy") as mock_gen, \
         patch("wildcards_gen.gui.save_and_preview", return_value=("path", "preview")):
        
        generate_dataset_handler(**base_kwargs)
        
        assert mock_gen.called
        args, kwargs = mock_gen.call_args
        assert "umap_n_neighbors" in kwargs
        assert "umap_min_dist" in kwargs
        assert "hdbscan_min_samples" in kwargs

def test_openimages_signature_sync(base_kwargs):
    base_kwargs["dataset_name"] = "Open Images"
    with patch("wildcards_gen.core.datasets.openimages.generate_openimages_hierarchy") as mock_gen, \
         patch("wildcards_gen.gui.save_and_preview", return_value=("path", "preview")):
        
        generate_dataset_handler(**base_kwargs)
        
        assert mock_gen.called
        args, kwargs = mock_gen.call_args
        assert "umap_n_neighbors" in kwargs
        assert "umap_min_dist" in kwargs
        assert "hdbscan_min_samples" in kwargs
