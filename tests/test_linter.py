"""
Semantic Linter Tests.

Tests for the linter module functionality.
"""
import pytest
import numpy as np
from wildcards_gen.core import linter

def test_model_registry():
    """Verify supported models exist."""
    assert "qwen3" in linter.MODELS
    assert "mpnet" in linter.MODELS
    assert "minilm" in linter.MODELS

def test_check_dependencies(mock_arranger_deps):
    """Test dependency check function."""
    # Should return True since we have the deps mocked in sys.modules
    result = linter.check_dependencies()
    assert result is True

def test_detect_outliers_small_input(mock_arranger_deps):
    """Test that small inputs return empty (too small to cluster)."""
    # Less than 3 items should return empty
    embeddings = np.array([[0.1], [0.2]])
    result = linter.detect_outliers_hdbscan(embeddings, threshold=0.1)
    assert result == []