import inspect
import pytest
from wildcards_gen.core.datasets import openimages, tencent

def _gui_smart_kwargs():
    """Mirror the keys the GUI passes to dataset generators."""
    return {
        "smart": True,
        "min_significance_depth": 4,
        "min_hyponyms": 50,
        "min_leaf_size": 5,
        "merge_orphans": True,
        "semantic_cleanup": False,
        "semantic_model": "minilm",
        "semantic_threshold": 0.1,
        "semantic_arrangement": True,
        "semantic_arrangement_threshold": 0.1,
        "semantic_arrangement_min_cluster": 5,
    }

def _assert_accepts_kwargs(fn, kwargs):
    """Verify that a function signature accepts all keys in kwargs."""
    sig = inspect.signature(fn)
    params = sig.parameters
    
    # Check for **kwargs which would accept everything
    has_var_keyword = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())
    if has_var_keyword:
        return

    missing = []
    for k in kwargs:
        if k not in params:
            missing.append(k)
            
    assert not missing, f"{fn.__module__}.{fn.__name__} missing params: {missing}"

def test_openimages_accepts_gui_smart_kwargs():
    """Contract: OpenImages generator must accept all GUI smart tuning kwargs."""
    _assert_accepts_kwargs(openimages.generate_openimages_hierarchy, _gui_smart_kwargs())

def test_tencent_accepts_gui_smart_kwargs():
    """Contract: Tencent generator must accept all GUI smart tuning kwargs."""
    _assert_accepts_kwargs(tencent.generate_tencent_hierarchy, _gui_smart_kwargs())

def test_openimages_has_apply_semantic_arrangement_symbol():
    """Contract: OpenImages must import apply_semantic_arrangement if it uses it."""
    # This checks if the symbol is available in the module namespace, 
    # preventing NameError at runtime.
    assert "apply_semantic_arrangement" in openimages.__dict__, \
        "openimages.py likely calls apply_semantic_arrangement but does not import it"
