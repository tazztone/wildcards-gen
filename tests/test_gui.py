
import pytest
from unittest.mock import patch, MagicMock, mock_open
import sys

# Completely mock gradio before importing gui
mock_gr = MagicMock()
sys.modules['gradio'] = mock_gr

from wildcards_gen import gui

def test_generate_dataset_handler_logic():
    """Test the generation wrapper function logic."""
    with patch('wildcards_gen.core.datasets.imagenet.generate_imagenet_tree') as mock_img, \
         patch('wildcards_gen.gui.StructureManager') as mock_mgr_cls, \
         patch('builtins.open', mock_open()) as mocked_file, \
         patch('os.makedirs'):
         
        mock_mgr = mock_mgr_cls.return_value
        mock_mgr.to_string.return_value = "root:\n- child"
        mock_img.return_value = {"root": ["child"]}
        
        path, content = gui.generate_dataset_handler(
            "ImageNet", "Standard", "animal.n.01", 3, "out.yaml",
            True, "none", True, False,
            6, 10, 3, False, False
        )
        
        assert path is not None
        assert "out.yaml" in path
        assert "root:" in content
        mock_img.assert_called_once()

def test_generate_dataset_handler_error():
    """Test error handling in generation."""
    # We patch inside gui.py's namespace for consistency
    with patch('wildcards_gen.gui.imagenet.generate_imagenet_tree', side_effect=Exception("Boom")):
        path, content = gui.generate_dataset_handler(
            "ImageNet", "Standard", "root", 3, "out.yaml",
            True, "none", True, False,
            6, 10, 3, False, False
        )
        assert path is None
        assert "Boom" in content

def test_generate_dataset_handler_openimages():
    """Test OpenImages handler passing bbox_only."""
    with patch('wildcards_gen.core.datasets.openimages.generate_openimages_hierarchy') as mock_oi, \
         patch('wildcards_gen.gui.StructureManager') as mock_mgr_cls, \
         patch('builtins.open', mock_open()), \
         patch('os.makedirs'):
         
        mock_mgr = mock_mgr_cls.return_value
        mock_mgr.to_string.return_value = "res"
        mock_oi.return_value = {}
        
        # Test valid call with bbox_only=True
        path, content = gui.generate_dataset_handler(
            "Open Images", "Smart", "", 3, "out.yaml",
            True, "none", False, False,
            4, 10, 3, False, True
        )
        
        assert path is not None
        mock_oi.assert_called_once()
        # Verify bbox_only was passed as True
        args, kwargs = mock_oi.call_args
        assert kwargs.get('bbox_only') is True

def test_create_handler_logic():
    """Test the LLM create handler logic."""
    with patch('wildcards_gen.gui.LLMEngine') as mock_engine_cls, \
         patch('wildcards_gen.gui.StructureManager') as mock_mgr_cls, \
         patch('builtins.open', mock_open()), \
         patch('os.makedirs'):
            
        mock_engine = mock_engine_cls.return_value
        mock_engine.generate_dynamic_structure.return_value = "topic:\n- item"
        
        mock_mgr = mock_mgr_cls.return_value
        mock_mgr.from_string.return_value = {"topic": ["item"]}
        mock_mgr.to_string.return_value = "topic:\n- item"
        
        path, content = gui.create_handler("Topic", "model", "key", "out.yaml")
        
        assert path is not None
        assert "topic:" in content
        mock_engine.generate_dynamic_structure.assert_called_once_with("Topic")

def test_create_handler_no_key():
    """Test create handler fails without API key."""
    path, content = gui.create_handler("Topic", "model", "", "out.yaml")
    assert path is None
    assert "API Key required" in content
