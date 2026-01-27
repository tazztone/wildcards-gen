"""
WordNet integration for hierarchy generation and gloss extraction.

Provides functions to:
- Load and query WordNet synsets
- Extract glosses (definitions) as instructions
- Build hierarchies from synsets
"""

import functools
import logging
from typing import Optional, Set, List, Any

import nltk
from nltk.corpus import wordnet as wn

logger = logging.getLogger(__name__)


def ensure_nltk_data() -> None:
    """Ensure NLTK WordNet data is available."""
    try:
        wn.ensure_loaded()
    except LookupError:
        logger.info("Downloading WordNet data...")
        try:
            nltk.download('wordnet', quiet=True)
            nltk.download('omw-1.4', quiet=True)
        except Exception as e:
            logger.error(f"Failed to download WordNet data: {e}")
            raise


@functools.lru_cache(maxsize=10000)
def get_synset_from_wnid(wnid: str) -> Optional[Any]:
    """
    Get a WordNet synset from a WNID (e.g., 'n02084071').
    
    Args:
        wnid: WordNet ID in format 'n12345678'
        
    Returns:
        Synset object or None if not found
    """
    try:
        if len(wnid) < 2:
            return None
        pos = wnid[0]
        offset = int(wnid[1:])
        return wn.synset_from_pos_and_offset(pos, offset)
    except Exception:
        return None


@functools.lru_cache(maxsize=10000)
def get_primary_synset(word: str) -> Optional[Any]:
    """
    Get the primary (most common) synset for a word.
    
    This filters out obscure or secondary meanings.
    """
    try:
        synsets = wn.synsets(word.replace(' ', '_'))
        if synsets:
            return synsets[0]
    except Exception:
        pass
    return None


def get_synset_name(synset) -> str:
    """Get clean name from synset (e.g., 'dog' from 'dog.n.01')."""
    return synset.lemmas()[0].name().replace('_', ' ')


def get_synset_gloss(synset) -> str:
    """
    Get the gloss (definition) of a synset.
    
    This is used as the default instruction text.
    Example: "a domesticated carnivorous mammal"
    """
    return synset.definition()


def get_synset_wnid(synset) -> str:
    """Get WNID from synset (e.g., 'n02084071')."""
    return f"{synset.pos()}{synset.offset():08d}"


def is_in_valid_set(synset, valid_wnids: Optional[Set[str]]) -> bool:
    """Check if synset's WNID is in the valid set."""
    if valid_wnids is None:
        return True
    return get_synset_wnid(synset) in valid_wnids


def get_all_descendants(
    synset,
    valid_wnids: Optional[Set[str]] = None
) -> List[str]:
    """
    Get all descendant names of a synset.
    
    Args:
        synset: The parent synset
        valid_wnids: Optional filter set
        
    Returns:
        Sorted list of descendant names
    """
    descendants = set()
    try:
        for s in synset.closure(lambda s: s.hyponyms()):
            name = get_synset_name(s)
            if valid_wnids:
                if is_in_valid_set(s, valid_wnids):
                    descendants.add(name)
            else:
                descendants.add(name)
    except Exception as e:
        logger.warning(f"Error traversing descendants of {synset}: {e}")

    return sorted(list(descendants))


# Categories to optionally blacklist (too abstract)
ABSTRACT_CATEGORIES = {
    'entity', 'abstraction', 'communication', 'measure',
    'attribute', 'state', 'event', 'act', 'group',
    'relation', 'possession', 'phenomenon'
}


def is_abstract_category(synset) -> bool:
    """Check if synset is an abstract category that should be blacklisted."""
    lemma = synset.name().split('.')[0]
    return lemma in ABSTRACT_CATEGORIES
