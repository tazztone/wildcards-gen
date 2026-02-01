
import pytest
import gradio as gr
from wildcards_gen.gui import launch_gui
from unittest.mock import MagicMock, patch
import os

def test_gui_inputs_have_info():
    """Verify that specific inputs have the info attribute set."""

    # Mock config
    with patch('wildcards_gen.gui.config') as mock_config, \
         patch('gradio.Blocks.launch'):

        # Mock values
        mock_config.api_key = None
        mock_config.model = 'test-model'
        mock_config.get.return_value = None

        # Patch ALL components to avoid real Gradio validation logic during launch
        with patch('gradio.Textbox') as MockTextbox, \
             patch('gradio.TextArea') as MockTextArea, \
             patch('gradio.Dropdown') as MockDropdown, \
             patch('gradio.Slider') as MockSlider, \
             patch('gradio.Checkbox') as MockCheckbox, \
             patch('gradio.Radio') as MockRadio, \
             patch('gradio.Markdown') as MockMarkdown, \
             patch('gradio.Button') as MockButton, \
             patch('gradio.File') as MockFile, \
             patch('gradio.Code') as MockCode, \
             patch('gradio.Group') as MockGroup, \
             patch('gradio.Column') as MockColumn, \
             patch('gradio.Row') as MockRow, \
             patch('gradio.Sidebar') as MockSidebar, \
             patch('gradio.Tab') as MockTab, \
             patch('gradio.Tabs') as MockTabs, \
             patch('gradio.Accordion') as MockAccordion, \
             patch('gradio.State') as MockState:

            launch_gui()

            # Helper to find a call by label
            def find_call_by_label(mock_obj, label):
                for call in mock_obj.call_args_list:
                    if call.kwargs.get('label') == label:
                        return call.kwargs
                return None

            # Verify cr_topic
            cr_topic_kwargs = find_call_by_label(MockTextbox, 'Topic')
            assert cr_topic_kwargs is not None, "Topic textbox not found"
            assert cr_topic_kwargs.get('info') == "The main subject to generate a taxonomy for."

            # Verify cat_terms
            cat_terms_kwargs = find_call_by_label(MockTextArea, 'Raw Terms')
            assert cat_terms_kwargs is not None, "Raw Terms textarea not found"
            assert cat_terms_kwargs.get('info') == "Paste a flat list of items to be organized into categories."

            # Verify en_yaml
            en_yaml_kwargs = find_call_by_label(MockTextArea, 'Existing YAML')
            assert en_yaml_kwargs is not None, "Existing YAML textarea not found"
            assert en_yaml_kwargs.get('info') == "The skeleton YAML structure you want to enrich with instructions."

            # Verify en_topic
            en_topic_kwargs = find_call_by_label(MockTextbox, 'Context / Goal')
            assert en_topic_kwargs is not None, "Context / Goal textbox not found"
            assert en_topic_kwargs.get('info') == "Context to guide the AI on what kind of instructions to generate."

            # Verify lint_model
            found_lint_info = False
            for call in MockDropdown.call_args_list:
                info_text = call.kwargs.get('info')
                if call.kwargs.get('label') == 'Model' and info_text and "qwen3 (Best/Slow)" in str(info_text):
                    found_lint_info = True
                    break
            assert found_lint_info, "Did not find Lint Model dropdown with correct info"

            # Verify lint_threshold
            lint_threshold_kwargs = find_call_by_label(MockSlider, 'Sensitivity')
            assert lint_threshold_kwargs is not None, "Sensitivity slider not found"
            assert lint_threshold_kwargs.get('info') == "Higher values = stricter checking (flags more items)."

            # Verify ds_filter
            ds_filter_kwargs = find_call_by_label(MockDropdown, 'Sub-Filter')
            assert ds_filter_kwargs is not None, "Sub-Filter dropdown not found"
            assert ds_filter_kwargs.get('info') == "Sub-sample size (1k = ImageNet-1k, 21k = Full ImageNet)."
