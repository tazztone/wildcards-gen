"""
CLI Integration Tests.

Smoke tests for CLI commands.
"""
import unittest
import subprocess
import os
import shutil

class TestCLIIntegration(unittest.TestCase):
    """End-to-End smoke tests for CLI commands."""
    
    @classmethod
    def setUpClass(cls):
        cls.test_dir = "tests/temp_output"
        os.makedirs(cls.test_dir, exist_ok=True)
        
    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir)

    def run_cli(self, args):
        """Helper to run CLI command."""
        cmd = ["uv", "run", "python", "-m", "wildcards_gen.cli"] + args
        return subprocess.run(cmd, capture_output=True, text=True, timeout=60)

    def test_help(self):
        """Test help command."""
        result = self.run_cli(["--help"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("dataset", result.stdout)

    def test_version_or_help(self):
        """Test basic CLI responsiveness."""
        result = self.run_cli(["dataset", "--help"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("imagenet", result.stdout.lower())

if __name__ == '__main__':
    unittest.main()
