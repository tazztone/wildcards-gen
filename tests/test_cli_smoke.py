import subprocess
import sys
import pytest

def test_cli_semantic_arrange_args():
    """
    Verify CLI accepts the --semantic-arrange flag and dependencies can be imported.
    Run via subprocess to ensure clean environment (simulating CLI usage).
    """
    # 1. Skip if lint extras (sentence-transformers) are not installed
    try:
        import sentence_transformers
    except ImportError:
        pytest.skip("lint extras (sentence-transformers) not installed")

    # 2. Verify CLI accepts the flags (using --help to avoid execution/download)
    # This ensures argparse is configured correctly for --semantic-arrange
    cmd_args = [
        sys.executable, "-m", "wildcards_gen.cli", 
        "dataset", "openimages", 
        "--smart", 
        "--semantic-arrange", 
        "--semantic-arrange-threshold", "0.5",
        "--help"
    ]
    result = subprocess.run(cmd_args, capture_output=True, text=True)
    assert result.returncode == 0, f"CLI failed to parse args: {result.stderr}"
    assert "--semantic-arrange" in result.stdout

    # 3. Verify Module Imports (catching NameErrors and dependency issues)
    # This mimics what would happen if the code reached the import statements
    # triggered by the flag execution.
    # explicit import of openimages (checks the fixed top-level import)
    # explicit import of arranger (checks sentence_transformers dependency)
    cmd_import = [
        sys.executable, "-c",
        "from wildcards_gen.core.datasets import openimages; "
        "from wildcards_gen.core import arranger; "
        "print('Imports Successful')"
    ]
    result_import = subprocess.run(cmd_import, capture_output=True, text=True)
    assert result_import.returncode == 0, f"Import check failed: {result_import.stderr}"
