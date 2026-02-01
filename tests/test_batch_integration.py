import unittest
import os
import shutil
import tempfile
import yaml
from unittest.mock import patch, MagicMock
from wildcards_gen.batch import BatchProcessor

class TestBatchIntegration(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.manifest_path = os.path.join(self.test_dir, "integration_manifest.yaml")
        self.output_dir = os.path.join(self.test_dir, "results")
        
        # Create a complex manifest
        self.manifest_data = {
            "config": {
                "output_dir": "results", # Relative to manifest
                "dataset": "tencent",
                "default_params": {"smart": True}
            },
            "jobs": [
                {"name": "baseline", "params": {"min_leaf_size": 10}}
            ],
            "matrix": {
                "axes": {
                    "min_leaf_size": [20, 30],
                    "semantic_threshold": [0.1, 0.2]
                }
            }
        }
        # Total jobs: 1 baseline + (2*2) matrix = 5 jobs
        
        with open(self.manifest_path, 'w') as f:
            yaml.dump(self.manifest_data, f)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    @patch('wildcards_gen.batch.run_single_job')
    def test_batch_report_generation(self, mock_run):
        """
        Verify that BatchProcessor correctly orchestrates 5 jobs and produces a valid report,
        even if some jobs fail.
        """
        def side_effect_safe(job):
            # Simulate failure for specific params
            if job.params.get('min_leaf_size') == 30 and job.params.get('semantic_threshold') == 0.2:
                return {"name": job.name, "success": False, "error": "Simulated Failure", "duration": 0.1}
            
            # Success path
            os.makedirs(os.path.dirname(job.output_path), exist_ok=True)
            with open(job.output_path, 'w') as f:
                f.write("Root:\n  - leaf1\n  - leaf2\n") # 1 Node, 2 Leaves
            
            return {"name": job.name, "dataset": job.dataset, "success": True, "duration": 0.5, "stats": {}}

        mock_run.side_effect = side_effect_safe
        
        processor = BatchProcessor(self.manifest_path, workers=1)
        processor.run()
        
        # Verify Report
        report_path = os.path.join(self.output_dir, "batch_report.md")
        self.assertTrue(os.path.exists(report_path), f"Report not found at {report_path}")
        
        with open(report_path, 'r') as f:
            content = f.read()
            
        # Check content
        self.assertIn("| baseline |", content)
        self.assertIn("| matrix_leaf_size20_threshold0.1 |", content)
        self.assertIn("❌ Simulated Failure", content)
        self.assertIn("| ✅ |", content)
        
        # Check stats counting (1 Node, 2 Leaves)
        # We expect "2 | 2" in the columns because the list itself counts as a node in recursion
        self.assertIn("| 2 | 2 |", content)

if __name__ == '__main__':
    unittest.main()