
import sys
from unittest.mock import MagicMock

# We need to mock nltk.corpus.wordnet BEFORE importing module that uses it
mock_wn = MagicMock()
# Mock the module in sys.modules so subsequent imports get the mock
if "nltk.corpus" not in sys.modules:
    sys.modules["nltk.corpus"] = MagicMock()
sys.modules["nltk.corpus"].wordnet = mock_wn

import pytest
from ruamel.yaml.comments import CommentedMap
from wildcards_gen.core.datasets.imagenet import generate_imagenet_tree
from wildcards_gen.core.structure import StructureManager


# Setup mock synsets
def create_mock_synset(name, lemmas, children=None, depth=0):
    s = MagicMock()
    s.name.return_value = name
    s.lemma_names.return_value = lemmas
    s.hyponyms.return_value = children if children else []
    s.min_depth.return_value = depth
    # closure for hyponyms
    # Simplified: return children as closure (depth 1 descendants)
    # Recursion logic in real WN is complex, but for test we just want 'descendants'.
    all_descendants = []
    if children:
        all_descendants.extend(children)
        # simplistic recurse if children have children? 
        # For this test, dog/cat children are leaves.
    s.closure.return_value = all_descendants

    s.pos.return_value = "n"
    s.offset.return_value = 12345
    
    # Mock lemmas
    mock_lemmas = []
    for l_name in lemmas:
        m_lemma = MagicMock()
        m_lemma.name.return_value = l_name
        mock_lemmas.append(m_lemma)
    s.lemmas.return_value = mock_lemmas
    
    return s



# Create a mini hierarchy
# entity (root)
#  -> animal (depth 1)
#      -> dog (depth 2) -> [poodle, beagle, pug] (small list)
#      -> cat (depth 2) -> [persian, siamese] (small list)
#  -> vehicle (depth 1) -> [car, truck, bike, plane, boat, bus, train, rocket, scooter, van, suv, sedan] (large list > 10)

s_poodle = create_mock_synset("poodle.n.01", ["poodle"])
s_beagle = create_mock_synset("beagle.n.01", ["beagle"])
s_pug = create_mock_synset("pug.n.01", ["pug"])
s_dog = create_mock_synset("dog.n.01", ["dog"], [s_poodle, s_beagle, s_pug], depth=2)

s_persian = create_mock_synset("persian.n.01", ["persian"])
s_siamese = create_mock_synset("siamese.n.01", ["siamese"])
s_cat = create_mock_synset("cat.n.01", ["cat"], [s_persian, s_siamese], depth=2)

s_animal = create_mock_synset("animal.n.01", ["animal"], [s_dog, s_cat], depth=1)

# Large list items
vehicle_children = [create_mock_synset(f"v{i}.n.01", [f"vehicle_{i}"]) for i in range(15)]
s_vehicle = create_mock_synset("vehicle.n.01", ["vehicle"], vehicle_children, depth=1)

s_entity = create_mock_synset("entity.n.01", ["entity"], [s_animal, s_vehicle], depth=0)

mock_wn.synset.return_value = s_entity


from unittest.mock import patch

def test_integration_pipeline_shaping():
    """
    Test that generate_imagenet_tree:
    1. Generates a structure
    2. Respects min_leaf_size (merging orphans)
    3. Preserves CommentedMap type
    """
    # Patch HDBSCAN to ensure clustering works (simulate 2 clusters)
    with patch('hdbscan.HDBSCAN') as MockHDBSCAN, \
         patch('wildcards_gen.core.arranger.check_dependencies', return_value=True):
         
        mock_clusterer = MockHDBSCAN.return_value
        # Configure mock to return valid clusters
        # 16 items being arranged (animal + vehicle children?)
        # Logic in imagenet runs arrange on CHILDREN.
        # e.g. Vehicle children (15 items).
        # We need to simulate that call.
        mock_clusterer.labels_ = [0]*15 # All in cluster 0
        mock_clusterer.probabilities_ = [1.0]*15
        
        mock_wn.synset.side_effect = lambda x: {
        "entity.n.01": s_entity,
        "animal.n.01": s_animal,
        "dog.n.01": s_dog,
        "cat.n.01": s_cat,
        "poodle.n.01": s_poodle,
        "beagle.n.01": s_beagle,
        "pug.n.01": s_pug,
        "persian.n.01": s_persian,
        "siamese.n.01": s_siamese,
        "vehicle.n.01": s_vehicle
    }.get(x)

    def side_effect_synsets(name):
        lookup = {
            "entity": [s_entity],
            "animal": [s_animal],
            "dog": [s_dog],
            "cat": [s_cat],
            "poodle": [s_poodle],
            "beagle": [s_beagle],
            "pug": [s_pug],
            "persian": [s_persian],
            "siamese": [s_siamese],
            "vehicle": [s_vehicle]
        }
        # handle vehicle children v0-v14
        if name.startswith("vehicle_"):
             # extract index? v0.n.01 lemma is vehicle_0
             idx = int(name.split('_')[1])
             return [vehicle_children[idx]]
        return lookup.get(name, [])
        
    mock_wn.synsets.side_effect = side_effect_synsets
 


    # Patch the 'wn' object inside the imagenet module
    with patch("wildcards_gen.core.datasets.imagenet.wn", mock_wn), \
         patch("wildcards_gen.core.datasets.imagenet.ensure_nltk_data"), \
         patch("wildcards_gen.core.datasets.imagenet.load_imagenet_1k_wnids", return_value=None):
         
         result = generate_imagenet_tree(
            root_synset_str="entity.n.01",
            smart=True,
            min_significance_depth=1, 
            min_leaf_size=5,
            merge_orphans=True,
            with_glosses=False
        )
    
    # Verify Type
    assert isinstance(result, CommentedMap)
    
    # Debug print
    import sys
    from ruamel.yaml import YAML
    yaml = YAML()
    print("\n--- Result Structure ---")
    yaml.dump(result, sys.stdout)

    # Verify Content
    assert "entity" in result
    entity = result["entity"]
    assert "animal" in entity
    assert "vehicle" in entity
    
    # Animal should have 'misc' containing orphans
    # Because Animal itself is depth 1 <= 1 (significant).
    # Its children were pruned/bubbled up.
    # So entity['animal'] should be a dict with 'misc'? 
    # OR if 'flatten_singles' ran...
    # Animal dict keys: ['misc']. (1 key).
    # flatten_singles promotes the value of 'misc'.
    # So animal becomes the list!
    assert isinstance(entity["animal"], list)
    assert len(entity["animal"]) >= 5
    assert "poodle" in entity["animal"]
    
    # Vehicle check
    # Vehicle depth 1. Significant.
    # Children bubble up.
    # Vehicle -> misc.
    # flatten_singles -> list.
    assert isinstance(entity["vehicle"], list)
    assert len(entity["vehicle"]) == 15
    assert "vehicle 0" in entity["vehicle"]


