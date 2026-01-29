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
        
        # We manually inspect the known wiring since we can't easily reflect Gradio's run-time events 
        # without launching the app (which hangs tests).
        # We verify that the functions exist and have the expected arg counts.
        
        # 1. Lint Handler: inputs=[file, model, threshold], return=[report]
        sig = inspect.signature(gui.lint_handler)
        params = list(sig.parameters)
        self.assertGreaterEqual(len(params), 3, "lint_handler needs at least file, model, threshold")
        self.assertIn("file_obj", params)
        self.assertIn("model", params)
        self.assertIn("threshold", params)

    def test_dataset_handler_wiring(self):
        """Check generate_dataset_handler signature matches the massive list of inputs."""
        sig = inspect.signature(gui.generate_dataset_handler)
        params = list(sig.parameters)
        
        # Current input list size in gui.py is ~16 items
        # ds_name, ds_strategy, ds_root, ds_depth, ds_out...
        expected_params = [
            "dataset_name", "strategy", "root", "depth", "output_name",
            "with_glosses", "filter_set", "strict_filter", "blacklist_abstract",
            "min_depth", "min_hyponyms", "min_leaf", "merge_orphans",
            "bbox_only", "exclude_subtree", "exclude_regex"
        ]
        
        for p in expected_params:
            self.assertIn(p, params, f"Missing {p} in generate_dataset_handler signature")

if __name__ == '__main__':
    unittest.main()
