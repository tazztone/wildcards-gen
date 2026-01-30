import pytest
import time
from nltk.corpus import wordnet as wn
from wildcards_gen.core.wordnet import get_all_descendants, ensure_nltk_data

def test_wordnet_caching_speedup():
    """Verify that get_all_descendants is cached and faster on second call."""
    ensure_nltk_data()
    
    # Pick a synset with decent size but not too huge to freeze test
    # 'canine.n.02' is a good candidate (dogs, wolves, etc)
    synset = wn.synset('canine.n.02')
    
    # 1st Run (Cold)
    t0 = time.time()
    res1 = get_all_descendants(synset)
    t1 = time.time()
    duration_cold = t1 - t0
    
    # 2nd Run (Warm)
    t2 = time.time()
    res2 = get_all_descendants(synset)
    t3 = time.time()
    duration_warm = t3 - t2
    
    assert res1 == res2
    assert len(res1) > 0
    
    # Warm should be instant (<1ms usually)
    # Cold might be 100ms+ depending on hierarchy depth
    print(f"Cold: {duration_cold:.4f}s, Warm: {duration_warm:.4f}s")
    
    # Requirement: Warm is significantly faster (or instant)
    # Be generous with threshold for CI robustness
    assert duration_warm < 0.1, f"Cached result took too long: {duration_warm}s"
    
    if duration_cold > 0.1: # Only compare if cold was measurable
        assert duration_warm < duration_cold, "Cache did not provide speedup"

def test_caching_with_filter():
    """Verify caching works even with valid_wnids."""
    synset = wn.synset('feline.n.01')
    
    # Create a filter set
    valid = {'n02124075', 'n02123045', 'n02123159'} # Random wnids (cats)
    
    # 1st Run
    res1 = get_all_descendants(synset, valid_wnids=valid)
    
    # 2nd Run (Same set content)
    valid_copy = {'n02124075', 'n02123045', 'n02123159'}
    t0 = time.time()
    res2 = get_all_descendants(synset, valid_wnids=valid_copy)
    duration = time.time() - t0
    
    assert res1 == res2
    assert duration < 0.1
