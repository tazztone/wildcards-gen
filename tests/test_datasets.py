
import pytest
from unittest.mock import patch, MagicMock
import os
import shutil
from wildcards_gen.core.datasets import imagenet, coco, openimages
from wildcards_gen.core.structure import StructureManager

@pytest.fixture
def mock_wn_fixture():
    """Mock WordNet and downloaders to avoid network calls."""
    with patch('wildcards_gen.core.wordnet.wn') as mock_wn, \
         patch('wildcards_gen.core.datasets.imagenet.wn') as mock_imagenet_wn, \
         patch('wildcards_gen.core.datasets.imagenet.ensure_imagenet_1k_data') as mock_1k, \
         patch('wildcards_gen.core.datasets.downloaders.download_file'), \
         patch('wildcards_gen.core.datasets.downloaders.unzip_file'):
        
        # Setup basic synset
        mock_synset = MagicMock()
        mock_synset.name.return_value = 'dog.n.01'
        mock_synset.definition.return_value = 'a domestic animal'
        
        lemma_mock = MagicMock()
        lemma_mock.name.return_value = 'dog'
        mock_synset.lemmas.return_value = [lemma_mock]
        
        mock_synset.hyponyms.return_value = [] # Leaf by default
        
        # Configure both mocks to behave the same
        for wn_mock in [mock_wn, mock_imagenet_wn]:
            wn_mock.synset.return_value = mock_synset
            wn_mock.synsets.return_value = [mock_synset]
            wn_mock.synset_from_pos_and_offset.return_value = mock_synset
        
        yield mock_wn

def test_imagenet_tree_generation(mock_wn_fixture):
    # Test that tree generation returns a structure
    structure = imagenet.generate_imagenet_tree(
        root_synset_str='entity.n.01',
        max_depth=2,
        with_glosses=True
    )
    assert structure is not None
    # With our mock, we expect 'dog' (name from lemma) to be in there
    # Since we mocked it as a leaf (no hyponyms), it should be a leaf list
    assert 'dog' in structure

def test_coco_generation():
    # Mock data loading
    mock_cats = [
        {"id": 1, "name": "bicycle", "supercategory": "vehicle"},
        {"id": 2, "name": "car", "supercategory": "vehicle"}
    ]
    
    with patch('wildcards_gen.core.datasets.coco.load_coco_categories', return_value=mock_cats), \
         patch('wildcards_gen.core.datasets.coco.get_primary_synset') as mock_prim, \
         patch('wildcards_gen.core.datasets.coco.get_synset_gloss', return_value="gloss"):
        
        structure = coco.generate_coco_hierarchy(with_glosses=True)
        
        assert 'vehicle' in structure
        assert 'bicycle' in structure['vehicle']
        assert 'car' in structure['vehicle']

def test_openimages_generation():
    # Mock data loading
    mock_hierarchy = {
        "LabelName": "/m/root",
        "Subcategories": [
            {"LabelName": "/m/cat1"},
            {"LabelName": "/m/cat2"}
        ]
    }
    mock_names = {"/m/root": "Entity", "/m/cat1": "Cat1", "/m/cat2": "Cat2"}
    
    with patch('wildcards_gen.core.datasets.openimages.load_openimages_data', return_value=(mock_hierarchy, mock_names)), \
         patch('wildcards_gen.core.datasets.openimages.get_primary_synset'), \
         patch('wildcards_gen.core.datasets.openimages.get_synset_gloss'):
         
        structure = openimages.generate_openimages_hierarchy(max_depth=2)
        
        # Should detect children and create structure
        assert 'Cat1' in structure or ('Entity' in structure and 'Cat1' in structure['Entity'])
        # Current logic might skip root 'Entity' wrapper if not explicit? 
        # Actually parse_hierarchy_node handles root special case.
