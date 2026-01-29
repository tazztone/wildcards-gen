import pytest
from unittest.mock import MagicMock, patch
from wildcards_gen import gui

def test_on_dataset_change_resets_analysis():
    """
    Test that changing the dataset resets the analysis report and hides the apply button.
    This would have caught the issue where changing datasets left stale analysis data.
    """
    # We need to mock gr.update because it's called inside on_dataset_change
    with patch('gradio.update') as mock_update:
        # Return unique mocks so we can distinguish them
        mock_update.side_effect = lambda **kwargs: kwargs

        # Call the handler that we consolidated
        # 498: def on_dataset_change(dataset_name, strategy):
        updates = gui.on_dataset_change("Open Images", "Smart")

        # The function returns a list of updates.
        # Based on gui.py:
        # visibility_updates (5) + info_update (1) + reset_analysis (2) = 8 items total
        assert len(updates) == 8
        
        # The last two items should be the analysis reset
        # gr.update(value=""),      # ds_analysis_output
        # gr.update(visible=False)  # apply_output_row
        
        analysis_output_update = updates[6]
        apply_row_update = updates[7]
        
        assert analysis_output_update['value'] == ""
        assert apply_row_update['interactive'] is False

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
