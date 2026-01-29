import pytest
from unittest.mock import patch, MagicMock, mock_open
import sys

# We don't hack sys.modules anymore because other tests load real gradio
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
            6, 10, 3, False, False,
            None, None
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
            6, 10, 3, False, False,
            None, None
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
            4, 10, 3, False, True,
            None, None
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

    path, content = gui.create_handler("Topic", "model", "", "out.yaml")
    assert path is None
    assert "API Key required" in content

def test_launch_gui_construction():
    """
    Test that the GUI layout can be constructed without errors.
    """
    with patch('wildcards_gen.gui.gr') as mock_gr, \
         patch('wildcards_gen.gui.config') as mock_config:
        
        # Setup config mocks
        mock_config.api_key = "test_key"
        mock_config.model = "test_model"
        mock_config.get.return_value = "info"
        
        # Configure the mock chain for unpacking
        # When ds_smart_preset.change() is called, it returns 4 items
        mock_gr.Radio.return_value.change.return_value = (MagicMock(), MagicMock(), MagicMock(), MagicMock())
        
        # Call the launch function
        gui.launch_gui(share=False)
        
        # Verify that Blocks was used (entered)
        mock_gr.Blocks.return_value.__enter__.assert_called()
        
        # Verify launch was called on the demo instance
        demo_instance = mock_gr.Blocks.return_value.__enter__.return_value
        demo_instance.launch.assert_called_once()

def test_update_ds_filename():
    """Test filename generation logic."""
    # ImageNet: Should include root
    f1 = gui.update_ds_filename("ImageNet", "animal.n.01", 3, "Standard")
    assert "imagenet_animal_d3.yaml" == f1
    
    # OpenImages: Should NOT include root even if passed (as UI might hold old value)
    f2 = gui.update_ds_filename("Open Images", "animal.n.01", 3, "Standard")
    assert "open_images_d3.yaml" == f2
    
    # OpenImages Smart
    f3 = gui.update_ds_filename("Open Images", "animal.n.01", 4, "Smart", 4, 50, 5)
    assert "open_images_d4_s4_f50_l5_smart.yaml" == f3
    
    # OpenImages Smart BBox
    f4 = gui.update_ds_filename("Open Images", "", 4, "Smart", 4, 50, 5, bbox_only=True)
    assert "open_images_d4_s4_f50_l5_smart_bbox.yaml" == f4
    
    # Tencent: Should NOT include root
    f5 = gui.update_ds_filename("Tencent ML-Images", "animal.n.01", 3, "Smart", 4, 100, 3)
    assert "tencent_mlimages_d3_s4_f100_l3_smart.yaml" == f5
