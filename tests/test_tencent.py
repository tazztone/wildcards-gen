import os
from unittest.mock import MagicMock, patch

import pytest
from ruamel.yaml.comments import CommentedMap

from wildcards_gen.core.datasets import tencent

# Sample header + one root + one child
SAMPLE_TENCENT_FILE = """category_index	category_id	index_of_parent_category	category name
0	n00002452	-1	thing
1	n05220461	0	body part
"""


@pytest.fixture
def mock_tencent_file(tmp_path):
    p = tmp_path / "hierarchy.txt"
    p.write_text(SAMPLE_TENCENT_FILE, encoding="utf-8")
    return str(p)


@patch("wildcards_gen.core.datasets.tencent.download_tencent_hierarchy")
@patch("wildcards_gen.core.datasets.tencent.get_synset_from_wnid")
@patch("wildcards_gen.core.datasets.tencent.get_synset_gloss")
@patch("wildcards_gen.core.datasets.tencent.ensure_nltk_data")
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

    # Convert to dict for existing assertions
    from wildcards_gen.core.builder import HierarchyBuilder
    from wildcards_gen.core.smart import SmartConfig

    builder = HierarchyBuilder(SmartConfig(enabled=False))
    # Wrap in root name to match old logic expectations
    assert hierarchy is not None
    hierarchy_dict = CommentedMap({hierarchy.name: builder._to_commented_map(hierarchy)})

    # Verify structure
    assert "thing" in hierarchy_dict
    assert "body part" in hierarchy_dict["thing"]

    # Verify instructions were added
    # For 'thing'
    # We can check if yaml usage is correct by dumping it or inspecting CommentedMap
    from ruamel.yaml import YAML

    yaml = YAML()
    import io

    stream = io.StringIO()
    yaml.dump(hierarchy_dict, stream)
    output = stream.getvalue()

    assert "thing:" in output
    assert "# instruction:" in output
