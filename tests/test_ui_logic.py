import pytest
from unittest.mock import MagicMock, patch
from wildcards_gen import gui

def test_on_dataset_change_logic():
    """
    Test that changing the dataset updates visibility and info text.
    Formerly also handled analysis reset, now optimized.
    """
    # We need to mock gr.update because it's called inside on_dataset_change
    with patch('gradio.update') as mock_update:
        # Return unique mocks so we can distinguish them
        mock_update.side_effect = lambda **kwargs: kwargs

        # Call the handler that we consolidated
        updates = gui.on_dataset_change("Open Images", "Smart")

        # The function returns a list of updates.
        # Based on gui.py: visibility_updates (5) + info_update (1) = 6 items total
        assert len(updates) == 6
        
        # Info update check
        info_update = updates[5]
        assert "Open Images V7" in info_update['value']

def test_update_ds_ui_logic():
    """Test the visibility logic for different datasets."""
    # ImageNet Standard
    updates = gui.update_ds_ui("ImageNet", "Standard")
    # returns [imagenet_group, strategy_interactive, smart_group, adv_filter, openimages_group]
    assert updates[0]['visible'] is True  # ImageNet group
    assert updates[2]['visible'] is False # Smart group (since strategy is Standard)
    assert updates[3]['visible'] is True  # Advanced filter (ImageNet only)
    assert updates[4]['visible'] is False # OpenImages group
    
    # OpenImages Smart
    updates = gui.update_ds_ui("Open Images", "Smart")
    assert updates[0]['visible'] is False # ImageNet group
    assert updates[2]['visible'] is True  # Smart group
    assert updates[4]['visible'] is True  # OpenImages group
