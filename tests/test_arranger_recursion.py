
import pytest
from unittest.mock import MagicMock, patch
import numpy as np

from wildcards_gen.core.arranger import arrange_hierarchy, extract_unique_keywords

def test_extract_unique_keywords_logic(mock_arranger_deps):
    """Test TF-IDF keyword extraction logic (mocked)."""
    mock_tfidf = mock_arranger_deps["tfidf_mod"].TfidfVectorizer.return_value
    
    # Mock fit_transform return value (matrix)
    mock_matrix = MagicMock()
    # Mocking sparse matrix toarray()[0]
    mock_matrix.__getitem__.return_value.toarray.return_value = [np.array([0.9, 0.1])] 
    mock_tfidf.fit_transform.return_value = mock_matrix
    
    # Mock feature names
    mock_tfidf.get_feature_names_out.return_value = np.array(["unique_term", "common_term"])
    
    cluster = ["unique term"]
    context = ["common term", "other stuff"]
    
    keywords = extract_unique_keywords(cluster, context, top_n=1)
    
    # Logic verification (dependent on mock sorting)
    mock_arranger_deps["tfidf_mod"].TfidfVectorizer.assert_called()
    assert isinstance(keywords, list)

def test_arrange_hierarchy_base_case(mock_arranger_deps):
    """Test recursion base case (small list)."""
    terms = ["a", "b", "c"]
    result = arrange_hierarchy(terms, max_leaf_size=10)
    assert result == ["a", "b", "c"]

def test_arrange_hierarchy_recursion_depth(mock_arranger_deps):
    """Test that recursion respects max depth."""
    terms = [f"item{i}" for i in range(20)]
    
    # Mock arrange_list to perform "splits" consistently
    with patch('wildcards_gen.core.arranger.arrange_list') as mock_arrange:
        # Side effect: always return 2 groups so we keep splitting if allowed
        def side_effect(t, **kwargs):
            mid = len(t) // 2
            return {"g1": t[:mid], "g2": t[mid:]}, []
            
        mock_arrange.side_effect = side_effect
        
        # Max depth 0 -> Should return original list (sorted) immediately if it fails?
        # Actually logic is: if len > max_leaf_size, try to cluster.
        # If max_depth is hit, we return list.
        # Wait, the check `len(terms) <= max_leaf_size or current_depth > max_depth` is at START.
        
        # So at depth 0, it continues. At depth 1, it checks.
        
        # Test 1: Hit max depth immediately
        result = arrange_hierarchy(terms, max_depth=0, current_depth=1, max_leaf_size=5)
        assert isinstance(result, list)
        assert len(result) == 20
        
        # Test 2: Allow 1 level of recursion
        # We need terms > max_leaf_size
        result_rec = arrange_hierarchy(terms, max_depth=1, current_depth=0, max_leaf_size=5)
        # Should return a dict with g1, g2
        assert isinstance(result_rec, dict)
        assert "g1" in result_rec
        assert "g2" in result_rec
        # And the values should be lists (because at depth 1, current_depth=1, max_depth=1 -> next call depth=2 > max -> returns list)
        assert isinstance(result_rec["g1"], list)
