
import pytest
from unittest.mock import patch, MagicMock, mock_open
import sys

# Mock gradio before importing gui to avoid import-time side effects or complex patching
# Check if wildcards_gen.gui is already imported
if 'wildcards_gen.gui' in sys.modules:
    del sys.modules['wildcards_gen.gui']

with patch.dict(sys.modules, {'gradio': MagicMock()}):
    from wildcards_gen import gui

def test_generate_dataset_logic():
    """Test the generation wrapper function logic."""
    # Mock the generators
    with patch('wildcards_gen.core.datasets.imagenet.generate_imagenet_tree') as mock_img, \
         patch('wildcards_gen.core.datasets.coco.generate_coco_hierarchy') as mock_coco, \
         patch('wildcards_gen.core.datasets.openimages.generate_openimages_hierarchy') as mock_oi, \
         patch('wildcards_gen.gui.StructureManager') as mock_mgr_cls:
         
        mock_mgr = mock_mgr_cls.return_value
        mock_mgr.to_string.return_value = "key: value"
        
        # Ensure generators return dicts, not Mocks (so ruamel doesn't choke)
        mock_img.return_value = {"root": ["child"]}
        mock_coco.return_value = {"coco": ["child"]}
        
        # Test ImageNet (Success case)
        # We need to mock open to avoid writing to disk
        with patch('builtins.open', mock_open()) as mocked_file, \
             patch('os.makedirs'):
            
            path, content = gui.generate_dataset("ImageNet", "root.n.01", 3, "out.yaml")
            
            # Debug failures
            if path is None:
                print(f"FAILED: {content}")
                
            assert path is not None
            assert "out.yaml" in path
            # Verify real output from StructureManager
            assert "root:" in content
            assert "child" in content
            mock_img.assert_called_once()
            mocked_file.assert_called()

def test_generate_dataset_error():
    """Test error handling in generation."""
    with patch('wildcards_gen.core.datasets.imagenet.generate_imagenet_tree', side_effect=Exception("Boom")):
        path, content = gui.generate_dataset("ImageNet", "root", 3, "out.yaml")
        assert path is None
        assert "Boom" in content
