"""
Semantic Linter Tests.

Tests for the linter module functionality.
"""
import unittest
from unittest.mock import patch, MagicMock
import numpy as np

class TestLinter(unittest.TestCase):
    def test_model_registry(self):
        """Verify supported models exist."""
        from wildcards_gen.core import linter
        self.assertIn("qwen3", linter.MODELS)
        self.assertIn("mpnet", linter.MODELS)
        self.assertIn("minilm", linter.MODELS)

    def test_check_dependencies(self):
        """Test dependency check function."""
        from wildcards_gen.core import linter
        # Should return True since we have the deps installed
        result = linter.check_dependencies()
        self.assertTrue(result)

    def test_detect_outliers_small_input(self):
        """Test that small inputs return empty (too small to cluster)."""
        from wildcards_gen.core import linter
        # Less than 3 items should return empty
        embeddings = np.array([[0.1], [0.2]])
        result = linter.detect_outliers_hdbscan(embeddings, threshold=0.1)
        self.assertEqual(result, [])

if __name__ == '__main__':
    unittest.main()
