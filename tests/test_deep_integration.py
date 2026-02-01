import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from wildcards_gen.gui import generate_dataset_handler

@pytest.fixture
def mock_ml_stack():
    """Mock the entire ML stack to allow deep integration testing without compute."""
    with patch('wildcards_gen.core.linter.load_embedding_model') as mock_load, \
         patch('wildcards_gen.core.linter.compute_list_embeddings') as mock_emb, \
         patch('wildcards_gen.core.arranger.compute_umap_embeddings') as mock_umap, \
         patch('hdbscan.HDBSCAN') as mock_hdbscan:
        
        # Mock model
        mock_model = MagicMock()
        mock_load.return_value = mock_model
        
        # Mock embeddings (random noise)
        def side_effect_emb(model, terms):
            return np.random.rand(len(terms), 384)
        mock_emb.side_effect = side_effect_emb
        
        # Mock UMAP (reduced noise)
        def side_effect_umap(embeddings, **kwargs):
            return np.random.rand(embeddings.shape[0], 5)
        mock_umap.side_effect = side_effect_umap
        
        # Mock HDBSCAN
        mock_instance = mock_hdbscan.return_value
        def side_effect_hdbscan(X):
            n = X.shape[0]
            mock_instance.labels_ = np.array([0] * n) # All in one cluster
            mock_instance.probabilities_ = np.array([0.9] * n)
        mock_instance.fit.side_effect = side_effect_hdbscan
        
        yield {
            "load": mock_load,
            "emb": mock_emb,
            "umap": mock_umap,
            "hdbscan": mock_hdbscan
        }

@pytest.fixture
def complex_smart_kwargs():
    """Exhaustive kwargs that exercise the entire Smart stack."""
    return {
        "dataset_name": "Tencent ML-Images", # Tencent uses the build_commented recursion
        "strategy": "Smart",
        "root": "1", # Root of Tencent
        "depth": 2,
        "output_name": "test_deep.yaml",
        "with_glosses": True,
        "filter_set": "none",
        "strict_filter": True,
        "blacklist_abstract": False,
        "min_depth": 2,
        "min_hyponyms": 2,
        "min_leaf": 2,
        "merge_orphans": True,
        "bbox_only": False,
        "semantic_clean": True,
        "semantic_model": "minilm",
        "semantic_threshold": 0.1,
        "semantic_arrange": True,
        "semantic_arrange_threshold": 0.1,
        "semantic_arrange_min_cluster": 2,
        "exclude_subtree": None,
        "exclude_regex": None,
        "semantic_arrange_method": "eom",
        "debug_arrangement": False,
        "umap_neighbors": 15,
        "umap_dist": 0.1,
        "min_samples": 2,
        "orphans_template": "misc",
        "fast_preview": True # Important for tencent to not download everything
    }

def test_full_stack_no_collisions(mock_ml_stack, complex_smart_kwargs):
    """
    Test that the entire flow from GUI -> Dataset -> Smart -> Arranger
    runs without any TypeError or parameter collisions.
    """
    # Mocking external data dependencies
    with patch('wildcards_gen.core.datasets.tencent.download_tencent_hierarchy', return_value='/tmp/mock.csv'), \
         patch('wildcards_gen.core.datasets.tencent.parse_hierarchy_file', return_value=(
             {
                 1: {'id': 'root', 'name': 'root', 'parent': -1},
                 2: {'id': 'animal', 'name': 'animal', 'parent': 1},
                 3: {'id': 'plant', 'name': 'plant', 'parent': 1},
                 4: {'id': 'dog', 'name': 'dog', 'parent': 2},
                 5: {'id': 'cat', 'name': 'cat', 'parent': 2},
                 6: {'id': 'bird', 'name': 'bird', 'parent': 2}
             },
             {1: [2, 3], 2: [4, 5, 6]},
             [1]
         )), \
         patch('wildcards_gen.gui.save_and_preview', return_value=("path", "preview")):
        
        # EXECUTE: This should flow all the way to arrange_list and back
        try:
            preview, summary, files = generate_dataset_handler(**complex_smart_kwargs)
        except TypeError as e:
            pytest.fail(f"Deep stack collision detected: {e}")
        except Exception as e:
            pytest.fail(f"Stack crashed with unexpected error: {e}")

        assert "Generation Complete" in summary
        assert mock_ml_stack["emb"].called
        assert mock_ml_stack["umap"].called
        
        # Verify that UMAP params actually made it through
        umap_call_kwargs = mock_ml_stack["umap"].call_args.kwargs
        assert umap_call_kwargs['n_neighbors'] == 15
        assert umap_call_kwargs['min_dist'] == 0.1
