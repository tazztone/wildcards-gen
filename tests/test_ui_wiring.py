"""
UI Wiring Tests.

Performs static analysis on the GUI wiring to ensure inputs match handler signatures.
"""
import unittest
import inspect
from wildcards_gen import gui

class TestUIWiring(unittest.TestCase):
    def test_handler_signatures(self):
        """Verify that UI components passed to handlers match the handler arguments."""
        
        # 1. Lint Handler
        sig = inspect.signature(gui.lint_handler)
        params = list(sig.parameters)
        self.assertGreaterEqual(len(params), 3, "lint_handler needs at least file, model, threshold")
        self.assertIn("file_obj", params)
        self.assertIn("model", params)
        self.assertIn("threshold", params)

    def test_dataset_handler_wiring(self):
        """Check generate_dataset_handler signature matches the exhaustive list of inputs."""
        sig = inspect.signature(gui.generate_dataset_handler)
        params = list(sig.parameters)
        
        # Modern parameter list as of v0.8.0
        expected_params = [
            "dataset_name", "strategy", "root", "depth", "output_name",
            "with_glosses", "filter_set", "strict_filter", "blacklist_abstract",
            "min_depth", "min_hyponyms", "min_leaf", "merge_orphans",
            "bbox_only",
            "semantic_clean", "semantic_model", "semantic_threshold",
            "semantic_arrange", "semantic_arrange_threshold", "semantic_arrange_min_cluster",
            "exclude_subtree", "exclude_regex",
            "semantic_arrange_method", "debug_arrangement",
            "umap_neighbors", "umap_dist", "min_samples", "orphans_template",
            "fast_preview"
        ]
        
        for p in expected_params:
            self.assertIn(p, params, f"Missing {p} in generate_dataset_handler signature")

if __name__ == '__main__':
    unittest.main()
