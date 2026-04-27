from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from wildcards_gen.core.datasets import imagenet, openimages, tencent
from wildcards_gen.core.smart import SmartConfig, TraversalBudget


def test_traversal_budget():
    budget = TraversalBudget(5)
    assert budget.consume(1)  # 1
    assert budget.consume(3)  # 4
    assert budget.consume(1)  # 5 (Limit reached)
    assert not budget.consume(1)


@patch("wildcards_gen.core.datasets.imagenet.ensure_imagenet_1k_data")
def test_imagenet_limit(mock_ensure):
    # Setup mock WordNet hierarchy
    with patch("wildcards_gen.core.datasets.imagenet.wn") as mock_wn:
        mock_root = MagicMock()
        mock_root.name.return_value = "vehicle.n.01"
        mock_root.lemmas.return_value = [MagicMock(name="vehicle")]
        mock_root.lemmas()[0].name.return_value = "vehicle"

        children = []
        for i in range(15):
            c = MagicMock()
            c.name.return_value = f"child{i}.n.01"
            c.lemmas.return_value = [MagicMock(name=f"child{i}")]
            c.lemmas()[0].name.return_value = f"child{i}"
            children.append(c)

        mock_root.hyponyms.return_value = children
        mock_wn.synset.return_value = mock_root

        preview_limit = 5
        result = imagenet.generate_imagenet_tree(
            root_synset_str="vehicle.n.01", max_depth=5, smart=True, preview_limit=preview_limit, with_glosses=False
        )

        assert result is not None
        assert result.name == "vehicle"  # Sample hierarchy uses 'vehicle'

        # Budget is 5. Root consumes 1. 4 children should be allowed.
        assert len(result.children) <= 4


@patch("wildcards_gen.core.datasets.openimages.ensure_openimages_data")
@patch("wildcards_gen.core.datasets.openimages.load_openimages_data")
def test_openimages_limit(mock_load, mock_ensure):
    # Mock data
    mock_ensure.return_value = ("hierarchy.json", "class-descriptions.csv")
    mock_hierarchy = {"LabelName": "/m/0", "Subcategory": [{"LabelName": "/m/1"} for _ in range(10)]}
    mock_names = {"/m/0": "Root"}
    for i in range(1, 11):
        mock_names[f"/m/{i}"] = f"Child{i}"

    mock_load.return_value = (mock_hierarchy, mock_names)

    with patch("wildcards_gen.core.datasets.openimages.get_synset_gloss", return_value="gloss"):
        result = openimages.generate_openimages_hierarchy(bbox_only=True, smart=True, preview_limit=3)
        assert result is not None
        assert result.name == "Root"
        assert len(result.children) <= 3


@patch("wildcards_gen.core.datasets.tencent.download_tencent_hierarchy")
@patch("wildcards_gen.core.datasets.tencent.parse_hierarchy_file")
@patch("wildcards_gen.core.datasets.tencent.get_synset_from_wnid")
def test_tencent_limit(mock_get_synset, mock_parse, mock_dl):
    mock_dl.return_value = "dummy.csv"
    mock_get_synset.return_value = None  # No synset found for dummy IDs

    # Create a hierarchy: Root -> 10 children
    categories: Dict[int, Any] = {0: {"id": "n0", "name": "Root", "parent": -1}}
    children_map: Dict[int, List[int]] = {0: []}
    for i in range(1, 11):
        categories[i] = {"id": f"n{i}", "name": f"Child {i}", "parent": 0}
        children_map[0].append(i)

    mock_parse.return_value = (categories, children_map, [0])

    result = tencent.generate_tencent_hierarchy(preview_limit=3)
    assert result is not None
    assert result.name == "Root"
    assert len(result.children) <= 3
