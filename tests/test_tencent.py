import os
import pytest
from unittest.mock import patch, MagicMock
from wildcards_gen.core.datasets import tencent

# Sample header + one root + one child
SAMPLE_TENCENT_FILE = """category_index	category_id	index_of_parent_category	category name
0	n00002452	-1	thing
1	n05220461	0	body part
"""

@pytest.fixture
def mock_tencent_file(tmp_path):
    p = tmp_path / "hierarchy.txt"
    p.write_text(SAMPLE_TENCENT_FILE, encoding='utf-8')
    return str(p)

@patch('wildcards_gen.core.datasets.tencent.download_tencent_hierarchy')
@patch('wildcards_gen.core.datasets.tencent.get_synset_from_wnid')
@patch('wildcards_gen.core.datasets.tencent.get_synset_gloss')
@patch('wildcards_gen.core.datasets.tencent.ensure_nltk_data')
def test_generate_tencent_hierarchy(mock_ensure, mock_gloss, mock_get_synset, mock_download, mock_tencent_file):
    # Setup mocks
    mock_download.return_value = mock_tencent_file
    
    # Mock WordNet calls
    # n00002452 = thing
    # n05220461 = body part
    
    mock_synset = MagicMock()
    mock_get_synset.return_value = mock_synset
    mock_gloss.return_value = "A definition."
    
    # Run generation
    hierarchy = tencent.generate_tencent_hierarchy(max_depth=5, with_glosses=True, min_leaf_size=0, merge_orphans=False)
    
    # Verify structure
    assert 'thing' in hierarchy
    assert 'body part' in hierarchy['thing']
    
    # Verify instructions were added
    # For 'thing'
    # We can check if yaml usage is correct by dumping it or inspecting CommentedMap
    from ruamel.yaml import YAML
    yaml = YAML()
    import io
    stream = io.StringIO()
    yaml.dump(hierarchy, stream)
    output = stream.getvalue()
    
    assert "thing:" in output
    assert "# instruction:" in output

@patch('wildcards_gen.core.datasets.tencent.download_tencent_hierarchy')
@patch('wildcards_gen.core.datasets.tencent.get_synset_from_wnid')
@patch('wildcards_gen.core.datasets.tencent.get_synset_gloss')
@patch('wildcards_gen.core.datasets.tencent.ensure_nltk_data')
@patch('wildcards_gen.core.smart.SmartConfig')
@patch('wildcards_gen.core.smart.apply_semantic_arrangement')
@patch('wildcards_gen.core.smart.apply_semantic_cleaning')
def test_generate_tencent_hierarchy_with_smart_flags(mock_cleaning, mock_arrangement, mock_smart_config, mock_ensure, mock_gloss, mock_get_synset, mock_download, mock_tencent_file):
    """Verify that new smart/arrangement flags are accepted and passed to SmartConfig."""
    mock_download.return_value = mock_tencent_file
    mock_get_synset.return_value = MagicMock()
    mock_arrangement.return_value = ({}, [], {})
    mock_cleaning.side_effect = lambda x, c: x
    
    # Configure mock
    conf = mock_smart_config.return_value
    conf.enabled = True
    conf.min_leaf_size = 5
    conf.min_hyponyms = 50
    conf.min_depth = 4
    conf.semantic_cleanup = True
    conf.semantic_arrangement = True

    
    # Call with new flags
    tencent.generate_tencent_hierarchy(
        smart=True,
        semantic_arrangement=True,
        semantic_arrangement_method="leaf",
        debug_arrangement=True
    )
    
    # Check that SmartConfig was initialized with all flags
    mock_smart_config.assert_called()
    _, kwargs = mock_smart_config.call_args
    assert kwargs['enabled'] is True
    assert kwargs['semantic_arrangement'] is True
    assert kwargs['semantic_arrangement_method'] == "leaf"
    assert kwargs['debug_arrangement'] is True