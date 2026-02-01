
import pytest
import numpy as np
from unittest.mock import MagicMock, patch

from wildcards_gen.core.arranger import compute_umap_embeddings, _arrange_single_pass

def test_compute_umap_embeddings_success(mock_arranger_deps):
    """Test that UMAP is called with correct parameters."""
    mock_umap_cls = mock_arranger_deps["umap"].UMAP
    mock_reducer = mock_umap_cls.return_value
    mock_reducer.fit_transform.return_value = np.zeros((20, 5))
    
    embeddings = np.random.rand(20, 384)
    
    result = compute_umap_embeddings(embeddings)
    
    # Check UMAP config
    mock_umap_cls.assert_called_with(
        n_neighbors=15,
        n_components=5,
        min_dist=0.1,
        metric='cosine',
        random_state=42
    )
    # Check result
    assert result.shape == (20, 5)

def test_compute_umap_embeddings_fallback_small_data(mock_arranger_deps):
    """Test fallback when sample size < n_neighbors."""
    embeddings = np.random.rand(10, 384) # 10 samples < 15 neighbors
    
    result = compute_umap_embeddings(embeddings)
    
    # Should return original embeddings unmodified
    assert result.shape == (10, 384)
    assert np.array_equal(result, embeddings)

def test_compute_umap_embeddings_import_error():
    """Test fallback when umap raises ImportError."""
    import sys
    with patch.dict(sys.modules, {'umap': None}):
        embeddings = np.random.rand(20, 384)
        result = compute_umap_embeddings(embeddings)
        
        assert np.array_equal(result, embeddings)

def test_arrange_single_pass_calls_umap(mock_arranger_deps):
    """Verify _arrange_single_pass calls compute_umap_embeddings."""
    # Clear cache to ensure UMAP is called
    from wildcards_gen.core import arranger
    arranger._UMAP_CACHE.clear()
    
    # Mock compute_umap_embeddings
    with patch('wildcards_gen.core.arranger.compute_umap_embeddings') as mock_compute:
        mock_compute.return_value = np.zeros((20, 5))
        
        # Mock HDBSCAN
        mock_hdbscan = mock_arranger_deps["clusterer"]
        mock_hdbscan.labels_ = np.zeros(20)
        mock_hdbscan.probabilities_ = np.zeros(20)
        
        terms = [f"term{i}" for i in range(20)]
        embeddings = np.random.rand(20, 384)
        
        _arrange_single_pass(terms, embeddings, min_cluster_size=2, threshold=0.1)
        
        mock_compute.assert_called_once()
        # Verify HDBSCAN was fit on the REDUCED embeddings
        mock_hdbscan.fit.assert_called_with(mock_compute.return_value)
