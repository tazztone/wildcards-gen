"""
ImageNet dataset hierarchy generator.

Generates skeleton YAML from ImageNet classes with WordNet glosses
as # instruction: comments.

Supports:
- Tree mode: Top-down from any root synset
- WNID mode: Bottom-up from specific WNIDs
- Filtering: ImageNet-1k or ImageNet-21k subsets
"""

import functools
import json
import logging
import re
from typing import Any, Dict, List, Optional, Set

from ruamel.yaml.comments import CommentedMap, CommentedSeq

from ..builder import TaxonomyNode
from ..config import config
from ..smart import TraversalBudget
from ..wordnet import (
    ensure_nltk_data,
    get_all_descendants,
    get_primary_synset,
    get_synset_from_wnid,
    get_synset_gloss,
    get_synset_name,
    get_synset_wnid,
    is_abstract_category,
    is_in_valid_set,
)
from .downloaders import ensure_imagenet_1k_data, ensure_imagenet_21k_data

try:
    from nltk.corpus import wordnet as wn
except ImportError:
    wn = None

logger = logging.getLogger(__name__)


@functools.lru_cache(maxsize=1)
def load_imagenet_1k_wnids() -> Set[str]:
    """Load the set of ImageNet-1k WNIDs."""
    logger.info("Loading ImageNet-1k class list...")
    list_path = ensure_imagenet_1k_data()
    try:
        with open(list_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        valid_wnids = set()
        for _key, value in data.items():
            if isinstance(value, list) and len(value) >= 1:
                valid_wnids.add(value[0])
        return valid_wnids
    except Exception as e:
        logger.error(f"Failed to load ImageNet-1k WNIDs: {e}")
        return set()


@functools.lru_cache(maxsize=1)
def load_imagenet_21k_wnids() -> Set[str]:
    """Load the set of ImageNet-21k WNIDs."""
    logger.info("Loading ImageNet-21k class list...")
    ids_path, _ = ensure_imagenet_21k_data()
    wnids = set()
    try:
        with open(ids_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    wnids.add(line)
    except Exception as e:
        logger.error(f"Failed to load ImageNet-21k WNIDs: {e}")
    return wnids


def build_taxonomy_tree(
    synset,
    valid_wnids: Optional[Set[str]],
    depth: int,
    max_depth: int,
    with_glosses: bool = True,
    strict_filter: bool = True,
    blacklist_abstract: bool = False,
    regex_list: Optional[List[re.Pattern]] = None,
    excluded_synsets: Optional[Set[str]] = None,
    budget: Optional[TraversalBudget] = None,
) -> Optional[TaxonomyNode]:
    """Pure extractor. No SmartConfig, no pruning, no shaping."""
    if budget and not budget.consume():
        return None
    name = get_synset_name(synset)

    # 1. Subtree Exclusion Check
    if excluded_synsets and synset in excluded_synsets:
        return None

    # 2. Regex Exclusion Check
    if regex_list:
        for pattern in regex_list:
            if pattern.search(name):
                return None

    # Blacklist check
    if blacklist_abstract and is_abstract_category(synset):
        return None

    # Strict primary synset check
    if strict_filter:
        primary = get_primary_synset(name)
        if primary and primary != synset:
            return None

    instruction = get_synset_gloss(synset) if with_glosses else None
    children = synset.hyponyms()

    # Leaf logic (at max_depth or no children)
    if depth >= max_depth or not children:
        descendants = get_all_descendants(synset, valid_wnids)
        if not descendants and (valid_wnids is None or is_in_valid_set(synset, valid_wnids)):
            descendants = [name]

        return TaxonomyNode(
            name=name,
            children=[],
            items=descendants or [],
            metadata={
                "instruction": instruction,
                "synset": synset,
                "wnid": get_synset_wnid(synset),
                "depth": depth,
                "is_root": (depth == 0),
            },
        )

    # Branch Logic
    child_nodes = []
    for child in children:
        child_node = build_taxonomy_tree(
            child,
            valid_wnids,
            depth + 1,
            max_depth,
            with_glosses,
            strict_filter,
            blacklist_abstract,
            regex_list,
            excluded_synsets,
            budget,
        )
        if child_node:
            child_nodes.append(child_node)

    if not child_nodes:
        # If no valid children, treat as leaf if it matches filter
        if valid_wnids is None or is_in_valid_set(synset, valid_wnids):
            return TaxonomyNode(
                name=name,
                items=[name],
                metadata={
                    "instruction": instruction,
                    "synset": synset,
                    "wnid": get_synset_wnid(synset),
                    "depth": depth,
                    "is_root": (depth == 0),
                },
            )
        return None

    return TaxonomyNode(
        name=name,
        children=child_nodes,
        metadata={
            "instruction": instruction,
            "synset": synset,
            "wnid": get_synset_wnid(synset),
            "depth": depth,
            "is_root": (depth == 0),
        },
    )


def generate_imagenet_tree(
    root_synset_str: str = "entity.n.01",
    max_depth: int = 4,
    filter_set: Optional[str] = None,
    with_glosses: bool = True,
    strict_filter: bool = True,
    blacklist_abstract: bool = False,
    exclude_regex: Optional[List[str]] = None,
    exclude_subtree: Optional[List[str]] = None,
    preview_limit: Optional[int] = None,
    **kwargs,  # Accept and ignore smart args for now
) -> Optional[TaxonomyNode]:
    """
    Generate ImageNet TaxonomyNode tree from a root synset.
    """
    ensure_nltk_data()

    # Load filter set
    valid_wnids = None
    if filter_set == "1k":
        valid_wnids = load_imagenet_1k_wnids()
    elif filter_set == "21k":
        valid_wnids = load_imagenet_21k_wnids()

    # Get root synset
    try:
        root_synset = wn.synset(root_synset_str)
    except Exception:
        logger.error(f"Could not find root synset: {root_synset_str}")
        return None

    # Prepare exclusions
    import re

    regex_list = [re.compile(r) for r in exclude_regex] if exclude_regex else []

    excluded_synsets = set()
    if exclude_subtree:
        for s_str in exclude_subtree:
            try:
                if s_str.startswith("n") and len(s_str) > 5 and s_str[1:].isdigit():
                    s = get_synset_from_wnid(s_str)
                else:
                    s = wn.synset(s_str)
                if s:
                    excluded_synsets.add(s)
            except Exception:
                logger.warning(f"Could not resolve excluded subtree: {s_str}")

    logger.info(f"Extracting raw hierarchy from {root_synset_str} (max_depth={max_depth})")

    budget = TraversalBudget(preview_limit)

    return build_taxonomy_tree(
        root_synset,
        valid_wnids,
        depth=0,
        max_depth=max_depth,
        with_glosses=with_glosses,
        strict_filter=strict_filter,
        blacklist_abstract=blacklist_abstract,
        regex_list=regex_list,
        excluded_synsets=excluded_synsets,
        budget=budget,
    )


def generate_imagenet_from_wnids(
    wnids: List[str],
    max_depth: int = 10,
    max_hypernym_depth: Optional[int] = None,
    with_glosses: bool = True,
) -> CommentedMap:
    """
    Generate hierarchy bottom-up from a list of WNIDs.

    Args:
        wnids: List of WordNet IDs (e.g., ['n02084071', 'n02121808'])
        max_depth: Maximum output depth
        max_hypernym_depth: Limit on hypernym chain length
        with_glosses: Add WordNet glosses as instructions

    Returns:
        CommentedMap with the hierarchy
    """
    ensure_nltk_data()

    if not wnids:
        return CommentedMap()

    logger.info(f"Processing {len(wnids)} WNIDs (bottom-up)...")

    # Build raw tree from hypernym paths
    raw_tree: Dict[str, Any] = {}

    for wnid in wnids:
        synset = get_synset_from_wnid(wnid)
        if not synset:
            continue

        paths = synset.hypernym_paths()
        if not paths:
            continue

        # Use primary path
        primary_path = paths[0]

        # Apply hypernym depth limit
        if max_hypernym_depth is not None and max_hypernym_depth > 0:
            path_to_use = primary_path[-max_hypernym_depth:]
        else:
            path_to_use = primary_path

        current = raw_tree
        for node in path_to_use:
            node_name = get_synset_name(node)
            if node_name not in current:
                current[node_name] = {}
            current = current[node_name]

    # Convert to CommentedMap with glosses
    def convert_tree(tree: dict, depth: int) -> CommentedMap:
        result = CommentedMap()

        for key, value in tree.items():
            if depth >= max_depth or not value:
                # Flatten: collect all leaves
                leaves = collect_leaves(value) if value else [key]
                if not leaves:
                    leaves = [key]
                seq = CommentedSeq(sorted(set(leaves)))
                result[key] = seq
            else:
                result[key] = convert_tree(value, depth + 1)

            # Add gloss
            if with_glosses:
                synset = get_primary_synset(key)
                if synset:
                    try:
                        result.yaml_add_eol_comment(
                            config.instruction_template.format(gloss=get_synset_gloss(synset)),
                            key,
                        )
                    except Exception:
                        pass

        return result

    def collect_leaves(tree: dict) -> List[str]:
        leaves = []
        for key, value in tree.items():
            if not value:
                leaves.append(key)
            else:
                leaves.extend(collect_leaves(value))
        return leaves

    return convert_tree(raw_tree, 0)
