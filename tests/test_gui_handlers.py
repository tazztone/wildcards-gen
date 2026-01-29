"""
GUI Handlers Unit Tests.

Tests the logic inside gui.py handlers without launching Gradio.
"""
import unittest
from unittest.mock import patch, MagicMock
from wildcards_gen import gui

class TestGUIHandlers(unittest.TestCase):
    
    @patch('wildcards_gen.gui.save_and_preview')
    @patch('wildcards_gen.gui.imagenet.generate_imagenet_tree')
    def test_generate_dataset_delegation(self, mock_gen, mock_save):
        """Test dataset handler calls correct generator logic."""
        mock_save.return_value = ("path", "content")
        
        # Test ImageNet delegation
        gui.generate_dataset_handler(
            "ImageNet", "Standard", "root.n.01", 3, "out.yaml",
            False, "none", True, False,
            4, 50, 5, False,  # valid ints + bool
            False, None, None
        )
        mock_gen.assert_called_once()
        
    def test_lint_handler_logic(self):
        """Test linter handler logic flow."""
        mock_file = MagicMock()
        mock_file.name = "test.yaml"
        
        # Patch the local import inside the function
        with patch('wildcards_gen.core.linter.lint_file') as mock_lint:
            # Case 1: No outliers
            mock_lint.return_value = {'issues': []}
            res = gui.lint_handler(mock_file, "qwen3", 0.1)
            self.assertIn("No outliers", res)
            
            # Case 2: Outliers found
            mock_lint.return_value = {
                'issues': [{
                    'path': 'root', 
                    'outliers': [{'term': 'bad', 'score': 0.9}]
                }]
            }
            res = gui.lint_handler(mock_file, "qwen3", 0.1)
            self.assertIn("Found 1 Potential Outliers", res)
            self.assertIn("| **0.90** | `bad` |", res)

    @patch('wildcards_gen.core.analyze.compute_dataset_stats')
    @patch('wildcards_gen.core.analyze.suggest_thresholds')
    @patch('wildcards_gen.core.datasets.imagenet.generate_imagenet_tree')
    def test_analyze_handler(self, mock_gen, mock_suggest, mock_stats):
        """Test analyze handler return structure."""
        
        mock_stats_obj = MagicMock()
        mock_stats_obj.max_depth = 5
        mock_stats_obj.total_nodes = 100
        mock_stats_obj.total_leaves = 50
        mock_stats_obj.to_dict.return_value = {'avg_branching': 2.0, 'avg_leaf_size': 5.0}
        
        mock_stats.return_value = mock_stats_obj
        mock_suggest.return_value = {'min_depth': 4, 'min_hyponyms': 50, 'min_leaf_size': 5}
        
        # Call handler
        report, d, h, l = gui.analyze_handler(
            "ImageNet", "root.n.01", 10, "none", True, False, False
        )
        
        self.assertIn("Analysis Report", report)
        self.assertEqual(d, 4)
        self.assertEqual(h, 50)
        self.assertEqual(l, 5)

if __name__ == '__main__':
    unittest.main()
