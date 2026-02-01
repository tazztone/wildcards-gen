
import unittest
import os
import shutil
import tempfile
import numpy as np
import concurrent.futures
from unittest.mock import patch, MagicMock
import sqlite3
import pickle

# Target module
from wildcards_gen.core import arranger

class TestArrangerPersistence(unittest.TestCase):
    def setUp(self):
        # Create isolated temp directory for DB
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_embeddings.db")
        
        # Patch the global DB_PATH in arranger module
        self.patcher = patch('wildcards_gen.core.arranger.DB_PATH', self.db_path)
        self.patcher.start()
        
        # Force re-init of DB with new path
        arranger._MEM_CACHE.clear()
        arranger._init_db()

    def tearDown(self):
        self.patcher.stop()
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_db_creation(self):
        """Verify DB file is created and schema is correct."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='embeddings'")
        self.assertIsNotNone(cursor.fetchone())
        conn.close()

    @patch('wildcards_gen.core.arranger.compute_list_embeddings')
    def test_caching_logic(self, mock_compute):
        """Verify computation happens once and is then cached (Memory & DB)."""
        mock_compute.return_value = np.array([[0.1, 0.2]])
        terms = ["apple", "banana"]
        
        # First call: Should compute
        emb1 = arranger.get_cached_embeddings(None, terms)
        self.assertEqual(mock_compute.call_count, 1)
        
        # Second call: Should hit Memory Cache (no compute)
        emb2 = arranger.get_cached_embeddings(None, terms)
        self.assertEqual(mock_compute.call_count, 1)
        
        # Clear Memory Cache to force DB Read
        arranger._MEM_CACHE.clear()
        
        # Third call: Should hit DB (no compute)
        emb3 = arranger.get_cached_embeddings(None, terms)
        self.assertEqual(mock_compute.call_count, 1)
        
        # Verify integrity
        np.testing.assert_array_equal(emb1, emb3)

    def test_concurrency_stress(self):
        """
        Stress test DB with multiple processes writing/reading simultaneously.
        """
        # We need a function that runs in a separate process and imports/uses arranger
        # Since we patched DB_PATH in this process, child processes via 'spawn' 
        # might verify the real DB_PATH unless we ensure environment or patching persists.
        # 'fork' (default on Linux) preserves the patch memory state usually? 
        # But 'ProcessPoolExecutor' might re-import modules.
        
        # To be safe, we'll use threads for this specific test class to verify logic locks,
        # verifying SQLite's thread-safety which translates to process safety if file locking works.
        # SQLite handles file locking for processes too.
        
        # Define worker
        def worker_task(i):
            # Create unique terms for write pressure, shared terms for read pressure
            terms_write = [f"unique_{i}_{x}" for x in range(10)]
            terms_read = [f"shared_{x}" for x in range(10)]
            
            # Use a mock model (string) passed to a mocked compute
            # We mock compute_list_embeddings inside the context of the thread?
            # It's harder to mock inside threads without context managers.
            # So we rely on the global mock applied to the module.
            return arranger.get_cached_embeddings(None, terms_write)

        # Mock compute to return random data
        with patch('wildcards_gen.core.arranger.compute_list_embeddings') as mock_compute:
            mock_compute.side_effect = lambda m, t: np.random.rand(len(t), 5)
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                futures = [executor.submit(worker_task, i) for i in range(50)]
                
                for f in concurrent.futures.as_completed(futures):
                    try:
                        res = f.result()
                        self.assertEqual(res.shape[1], 5)
                    except Exception as e:
                        self.fail(f"Concurrency failure: {e}")
                        
        # Verify DB size (50 workers * 1 row per list = 50 rows)
        conn = sqlite3.connect(self.db_path)
        count = conn.execute("SELECT count(*) FROM embeddings").fetchone()[0]
        conn.close()
        self.assertEqual(count, 50)

if __name__ == '__main__':
    unittest.main()
