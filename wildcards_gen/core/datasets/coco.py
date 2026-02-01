"""
COCO dataset hierarchy generator.

Generates skeleton YAML from COCO categories with WordNet glosses
as # instruction: comments.
"""

import json
import functools
import logging
from typing import Dict, List, Any

from ruamel.yaml.comments import CommentedMap, CommentedSeq

from ..structure import StructureManager
from ..config import config
from ..wordnet import ensure_nltk_data, get_primary_synset, get_synset_gloss
from .downloaders import ensure_coco_data

logger = logging.getLogger(__name__)


@functools.lru_cache(maxsize=1)
def load_coco_categories() -> List[Dict[str, Any]]:
    """Load COCO categories from annotations file."""
    json_path = ensure_coco_data()
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['categories']


def get_coco_gloss(category_name: str) -> str:
    """Get WordNet gloss for a COCO category."""
    synset = get_primary_synset(category_name)
    if synset:
        return get_synset_gloss(synset)
    return f"Items in the {category_name} category"


def generate_coco_hierarchy(
    with_glosses: bool = True,
    max_depth: int = 10
) -> CommentedMap:
    """
    Generate hierarchy from COCO dataset categories.
    
    COCO has a simple 2-level hierarchy: supercategory -> category
    
    Args:
        with_glosses: Add WordNet glosses as instructions
        max_depth: Not really used for COCO (already shallow)
        
    Returns:
        CommentedMap with the hierarchy
    """
    ensure_nltk_data()
    
    logger.info("Generating COCO hierarchy...")
    categories = load_coco_categories()
    
    structure_mgr = StructureManager()
    result = CommentedMap()
    
    # Group by supercategory
    grouped: Dict[str, List[str]] = {}
    for cat in categories:
        supercat = cat['supercategory']
        name = cat['name']
        if supercat not in grouped:
            grouped[supercat] = []
        grouped[supercat].append(name)
    
    # Build structure
    for supercat, items in sorted(grouped.items()):
        # Get instruction for supercategory
        instruction = get_coco_gloss(supercat) if with_glosses else None
        
        # Create leaf list
        seq = CommentedSeq(sorted(items))
        result[supercat] = seq
        
        if instruction:
            try:
                result.yaml_add_eol_comment(config.instruction_template.format(gloss=instruction), supercat)
            except Exception:
                pass
    
    logger.info(f"Generated {len(grouped)} supercategories with {len(categories)} items")
    return result
