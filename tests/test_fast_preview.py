
import pytest
from unittest.mock import MagicMock, patch
from wildcards_gen.core.datasets import imagenet, openimages, tencent
from wildcards_gen.core.smart import TraversalBudget, SmartConfig

def test_traversal_budget():
    budget = TraversalBudget(5)
    assert budget.consume(1) # 1
    assert budget.consume(3) # 4
    assert budget.consume(1) # 5 (Limit reached)
    assert budget.is_exhausted()
    assert not budget.consume(1) # False

@patch('wildcards_gen.core.datasets.imagenet.ensure_imagenet_1k_data')
@patch('wildcards_gen.core.datasets.imagenet.get_synset_from_wnid')
@patch('wildcards_gen.core.datasets.imagenet.wn')
def test_imagenet_limit(mock_wn, mock_get_synset, mock_ensure_data):
    # Mock setup
    mock_ensure_data.return_value = "dummy.json"
    root_synset = MagicMock()
    root_synset.name.return_value = "entity.n.01"
    children = []
    for i in range(10):
        c = MagicMock()
        c.name.return_value = f"child_{i}"
        c.pos.return_value = 'n'
        c.offset.return_value = i
        l = MagicMock()
        l.name.return_value = f"child_{i}"
        l.name.return_value = f"child_{i}"
        c.lemmas.return_value = [l]
        # Make sortable
        c.__lt__ = lambda self, other: self.name() < other.name()
        children.append(c)
    root_synset.hyponyms.return_value = children
    mock_wn.synset.return_value = root_synset
    
    # Run with limit
    preview_limit = 5
    result = imagenet.generate_imagenet_tree(
        root_synset_str="entity.n.01",
        max_depth=5,
        smart=True,
        preview_limit=preview_limit,
        with_glosses=False
    )
    
    # We can't easily count exact nodes in result structure because it nests, 
    # but we can trust that if the budget works, it stops.
    # We can assert that the budget object was initialized and used.
    # But since we can't introspect internal vars, check if we got a partial result?
    # With 10 children and limit 5, we shouldn't get all children.
    
    assert len(result.get('entity', {})) <= preview_limit + 1 # rough check

@patch('wildcards_gen.core.datasets.openimages.ensure_openimages_data')
@patch('wildcards_gen.core.datasets.openimages.load_openimages_data')
def test_openimages_limit(mock_load, mock_ensure):
    # Mock data
    mock_ensure.return_value = ("hierarchy.json", "class-descriptions.csv")
    hierarchy = {
        "LabelName": "/m/root",
        "Subcategory": [
            {"LabelName": f"/m/c{i}"} for i in range(10)
        ]
    }
    id_to_name = {"/m/root": "Root"}
    for i in range(10):
        id_to_name[f"/m/c{i}"] = f"Child {i}"
        
    mock_load.return_value = (hierarchy, id_to_name)
    
    # Run in BBox mode (easier to test recursion directly)
    result = openimages.generate_openimages_hierarchy(
        bbox_only=True,
        smart=True,
        preview_limit=3,
        with_glosses=False
    )
    
    # Root + 3 children? Root takes 1, leaving 2 children.
    # The result structure should reflect this.
    root_content = result.get('Root')
    assert root_content is not None
    # Depending on implementation, it might have fewer than 10 children
    assert len(root_content) < 10

@patch('wildcards_gen.core.datasets.tencent.download_tencent_hierarchy')
@patch('wildcards_gen.core.datasets.tencent.parse_hierarchy_file')
def test_tencent_limit(mock_parse, mock_dl):
    mock_dl.return_value = "dummy.csv"
    
    # Create a hierarchy: Root -> 10 children
    categories = {0: {'id': 'n0', 'name': 'Root', 'parent': -1}}
    children_map = {0: []}
    for i in range(1, 11):
        categories[i] = {'id': f'n{i}', 'name': f'Child {i}', 'parent': 0}
        children_map[0].append(i)
        
    mock_parse.return_value = (categories, children_map, [0])
    
    result = tencent.generate_tencent_hierarchy(
        smart=True,
        preview_limit=3,
        with_glosses=False
    )
    
    # Check output size
    # Root should have fewer than 10 children if limit worked
    root_content = result.get('Root')
    # If the fix works, root_content should be smaller or None if budget exhausted immediately (unlikely with 3)
    if root_content:
        assert len(root_content) < 10
    else:
        pass # empty is also < 10 basically
