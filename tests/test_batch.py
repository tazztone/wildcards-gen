
import unittest
from unittest.mock import patch, MagicMock
import os
import shutil
import yaml
from wildcards_gen.batch import BatchProcessor, JobConfig

class TestBatchProcessor(unittest.TestCase):
    def setUp(self):
        self.test_dir = "tests/temp_batch"
        os.makedirs(self.test_dir, exist_ok=True)
        self.manifest_path = os.path.join(self.test_dir, "manifest.yaml")
        
        # Create a sample manifest
        self.manifest_data = {
            "config": {
                "output_dir": "output_test",
                "dataset": "tencent"
            },
            "jobs": [
                {
                    "name": "explicit_job",
                    "params": {"depth": 5}
                }
            ],
            "matrix": {
                "base_params": {"smart": True},
                "axes": {
                    "min_leaf_size": [10, 20],
                    "semantic_threshold": [0.1]
                }
            }
        }
        with open(self.manifest_path, 'w') as f:
            yaml.dump(self.manifest_data, f)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_manifest_parsing(self):
        processor = BatchProcessor(self.manifest_path)
        
        # Should have 1 explicit + 2 matrix jobs = 3 total
        self.assertEqual(len(processor.jobs), 3)
        
        # Check Explicit
        job1 = processor.jobs[0]
        self.assertEqual(job1.name, "explicit_job")
        self.assertEqual(job1.params['depth'], 5)
        
        # Check Matrix
        matrix_jobs = processor.jobs[1:]
        self.assertEqual(len(matrix_jobs), 2)
        self.assertTrue(any(j.params['min_leaf_size'] == 10 for j in matrix_jobs))
        self.assertTrue(any(j.params['min_leaf_size'] == 20 for j in matrix_jobs))

    @patch('wildcards_gen.batch.run_single_job')
    def test_execution_serial(self, mock_run):
        mock_run.return_value = {
            "name": "test", "dataset": "tencent", "success": True, 
            "duration": 0.1, "stats": {}
        }
        
        processor = BatchProcessor(self.manifest_path, workers=1)
        processor.run()
        
        self.assertEqual(mock_run.call_count, 3)

    @patch('concurrent.futures.as_completed')
    @patch('concurrent.futures.ProcessPoolExecutor')
    def test_execution_parallel(self, mock_executor_cls, mock_as_completed):
        # Mock executor context manager
        mock_executor = MagicMock()
        mock_executor_cls.return_value.__enter__.return_value = mock_executor
        
        # Mock Futures
        mock_future = MagicMock()
        mock_future.result.return_value = {"success": True, "name": "job", "duration": 0.1, "dataset": "test"}
        
        # Configure submit to return the mock future
        mock_executor.submit.return_value = mock_future
        
        # Configure as_completed to yield the futures immediately
        # We expect 3 jobs, so yield 3 futures
        mock_as_completed.return_value = [mock_future, mock_future, mock_future]
        
        processor = BatchProcessor(self.manifest_path, workers=2)
        processor.run()
        
        # Ensure submit was called 3 times
        self.assertEqual(mock_executor.submit.call_count, 3)

if __name__ == '__main__':
    unittest.main()
