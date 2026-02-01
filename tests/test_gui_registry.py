import ast
import os
import pytest

def get_gui_components():
    """Extract all gradio component calls from gui.py."""
    gui_path = os.path.join(os.path.dirname(__file__), "../wildcards_gen/gui.py")
    with open(gui_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())
    
    components = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            # Check if it's a gr.Slider, gr.Checkbox, etc.
            if isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "gr":
                    if node.func.attr in ["Slider", "Checkbox", "Dropdown", "Textbox", "Radio"]:
                        # Extract line number and kwargs
                        kwargs = {kw.arg: kw.value for kw in node.keywords}
                        components.append({
                            "type": node.func.attr,
                            "line": node.lineno,
                            "kwargs": kwargs
                        })
    return components

def test_tooltip_coverage():
    """Verify that all relevant UI inputs have educational tooltips (info field)."""
    components = get_gui_components()
    
    # Exclude components that don't absolutely need info (like the HF token or generic textboxes)
    # But for this milestone, we want to be strict on the Smart Tuning group.
    
    # We define the line range for the Configuration Sidebar
    # Based on gui.py, it's roughly between 580 and 700
    
    missing_info = []
    for comp in components:
        if 580 <= comp["line"] <= 700:
            if "info" not in comp["kwargs"]:
                # Special cases: some Textboxes might be self-explanatory but we want tooltips for all configuration
                missing_info.append(f"{comp['type']} at line {comp['line']}")
                
    assert not missing_info, f"The following components are missing 'info=' tooltips: {missing_info}"

def test_smart_preset_integrity():
    """Verify that SMART_PRESETS contains valid configurations."""
    from wildcards_gen.core.presets import SMART_PRESETS
    
    for name, params in SMART_PRESETS.items():
        assert len(params) == 7, f"Preset {name} should have 7 parameters"
        assert isinstance(params[0], int), "min_depth should be int"
        assert isinstance(params[1], int), "min_hyponyms should be int"
        assert isinstance(params[2], int), "min_leaf should be int"
        assert isinstance(params[3], bool), "merge_orphans should be bool"
        assert isinstance(params[4], bool), "semantic_clean should be bool"
        assert isinstance(params[5], bool), "semantic_arrange should be bool"
        assert params[6] in ['eom', 'leaf'], "method should be eom or leaf"
