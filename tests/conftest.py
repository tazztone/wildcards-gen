import pytest
import sys
from unittest.mock import MagicMock, patch

@pytest.fixture
def mock_synset_factory():
    def create_mock_synset(name, lemmas, children=None, depth=0):
        s = MagicMock()
        s.name.return_value = name
        s.lemma_names.return_value = lemmas
        s.hyponyms.return_value = children if children else []
        s.min_depth.return_value = depth

        # closure for hyponyms (simplified: just immediate children for this mock)
        all_descendants = []
        if children:
            all_descendants.extend(children)
        s.closure.return_value = all_descendants

        s.pos.return_value = "n"
        s.offset.return_value = abs(hash(name)) % 10000000

        # Mock lemmas
        mock_lemmas = []
        for l_name in lemmas:
            m_lemma = MagicMock()
            m_lemma.name.return_value = l_name
            mock_lemmas.append(m_lemma)
        s.lemmas.return_value = mock_lemmas

        # Make sortable for stable ordering in tests
        s.__lt__ = lambda self, other: self.name() < other.name()

        return s
    return create_mock_synset

@pytest.fixture
def sample_hierarchy(mock_synset_factory):
    # Create the standard hierarchy used in tests
    # entity -> [animal, vehicle]
    # animal -> [dog, cat]
    # vehicle -> [v0..v14]

    # Leaves
    s_poodle = mock_synset_factory("poodle.n.01", ["poodle"])
    s_beagle = mock_synset_factory("beagle.n.01", ["beagle"])
    s_pug = mock_synset_factory("pug.n.01", ["pug"])
    s_dog = mock_synset_factory("dog.n.01", ["dog"], [s_poodle, s_beagle, s_pug], depth=2)

    s_persian = mock_synset_factory("persian.n.01", ["persian"])
    s_siamese = mock_synset_factory("siamese.n.01", ["siamese"])
    s_cat = mock_synset_factory("cat.n.01", ["cat"], [s_persian, s_siamese], depth=2)

    s_animal = mock_synset_factory("animal.n.01", ["animal"], [s_dog, s_cat], depth=1)

    vehicle_children = [mock_synset_factory(f"v{i}.n.01", [f"vehicle_{i}"]) for i in range(15)]
    s_vehicle = mock_synset_factory("vehicle.n.01", ["vehicle"], vehicle_children, depth=1)

    s_entity = mock_synset_factory("entity.n.01", ["entity"], [s_animal, s_vehicle], depth=0)

    # Helper to lookup by name
    lookup = {
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
    }
    for vc in vehicle_children:
        lookup[vc.name()] = vc

    return {
        "root": s_entity,
        "lookup": lookup,
        "vehicle_children": vehicle_children
    }

@pytest.fixture
def mock_wn(sample_hierarchy):
    """
    Patches nltk.corpus.wordnet and related modules.
    Configured with sample_hierarchy by default.
    """
    mock_wn_obj = MagicMock()

    # Configure synset lookup
    def side_effect_synset(name):
        return sample_hierarchy["lookup"].get(name)

    mock_wn_obj.synset.side_effect = side_effect_synset

    # Configure synsets lookup (lemma -> synsets)
    def side_effect_synsets(name):
        res = []
        # specific handling for test strings if they match keys exactly (simplified)
        # Real wordnet does lemma search.
        # Here we iterate over all mock synsets and check lemmas
        for s in sample_hierarchy["lookup"].values():
            if name in s.lemma_names():
                res.append(s)
        return res

    mock_wn_obj.synsets.side_effect = side_effect_synsets

    # Patch wherever 'wn' is used
    with patch("wildcards_gen.core.wordnet.wn", mock_wn_obj), \
         patch("wildcards_gen.core.datasets.imagenet.wn", mock_wn_obj):
        # We also attempt to patch nltk.corpus.wordnet if imported directly elsewhere
        with patch("nltk.corpus.wordnet", mock_wn_obj):
            yield mock_wn_obj

@pytest.fixture
def mock_arranger_deps():
    """
    Mocks hdbscan, sklearn, and their submodules to prevent ImportErrors
    when these optional dependencies are missing.
    Returns the dictionary of mocks used.
    """
    mock_hdbscan_module = MagicMock()
    mock_sklearn = MagicMock()
    mock_sklearn_metrics = MagicMock()
    mock_sklearn_metrics_pairwise = MagicMock()

    mock_sklearn.metrics = mock_sklearn_metrics
    mock_sklearn.metrics.pairwise = mock_sklearn_metrics_pairwise

    modules_to_patch = {
        "hdbscan": mock_hdbscan_module,
        "sklearn": mock_sklearn,
        "sklearn.metrics": mock_sklearn_metrics,
        "sklearn.metrics.pairwise": mock_sklearn_metrics_pairwise
    }

    with patch.dict(sys.modules, modules_to_patch):
        # Configure standard happy path
        MockHDBSCAN = MagicMock()
        mock_hdbscan_module.HDBSCAN = MockHDBSCAN
        mock_clusterer = MockHDBSCAN.return_value
        mock_clusterer.fit.return_value = None

        yield {
            "hdbscan": mock_hdbscan_module,
            "HDBSCAN": MockHDBSCAN,
            "clusterer": mock_clusterer,
            "sklearn": mock_sklearn
        }

@pytest.fixture(autouse=True)
def clear_caches():
    # Clear lru_caches to ensure mocks are used
    from wildcards_gen.core.wordnet import get_primary_synset
    get_primary_synset.cache_clear()
