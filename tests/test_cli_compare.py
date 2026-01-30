
import pytest
import sys
from unittest.mock import patch
from wildcards_gen.cli import main
from wildcards_gen.core.structure import StructureManager

def test_cli_compare(tmp_path, capsys):
    """Test the full CLI comparison flow."""
    f1 = tmp_path / "file1.yaml"
    f2 = tmp_path / "file2.yaml"
    
    # Create valid structures
    mgr = StructureManager()
    s1 = mgr.create_empty_structure()
    mgr.add_leaf_list(s1, "animals", ["dog", "cat"])
    
    s2 = mgr.create_empty_structure()
    mgr.add_leaf_list(s2, "animals", ["dog", "cat", "bird"])
    
    mgr.save_structure(s1, str(f1))
    mgr.save_structure(s2, str(f2))
    
    # Invoke main with arguments
    with patch.object(sys, 'argv', ["wildcards-gen", "compare", str(f1), str(f2)]):
        main()
    
    captured = capsys.readouterr()
    
    # Assertions
    assert "Stability Report" in captured.out
    assert "Content Stability (Jaccard)" in captured.out
    # Jaccard should be 2/3 = 0.6666
    assert "0.6667" in captured.out or "0.6666" in captured.out


def test_cli_compare_missing_dependency(tmp_path, capsys, monkeypatch):
    """Test graceful failure if sklearn is missing."""
    import wildcards_gen.analytics.metrics
    from pathlib import Path
    
    # Simulate missing dependency
    monkeypatch.setattr(wildcards_gen.analytics.metrics, "check_dependencies", lambda: False)
    
    f1 = tmp_path / "file1.yaml"
    f2 = tmp_path / "file2.yaml"
    # Need files to exist even for fail case to pass parser
    Path(f1).touch()
    Path(f2).touch()
    
    with patch.object(sys, 'argv', ["wildcards-gen", "compare", str(f1), str(f2)]):
        main()

    captured = capsys.readouterr()
    assert "Analysis requires extra dependencies" in captured.out

