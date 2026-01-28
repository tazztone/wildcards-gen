"""
Unified CLI for wildcards-gen.

Commands:
- dataset: Generate from CV datasets (ImageNet, COCO, OpenImages)
- categorize: Categorize flat term list (LLM-powered)
- create: Generate empty taxonomy for a topic (LLM-powered)
- enrich: Add/improve instructions in existing YAML (LLM-powered)
"""

import argparse
import logging
import sys
import os
from typing import Optional

from .core.config import config
from .core.structure import StructureManager
from .core.datasets.imagenet import generate_imagenet_tree, generate_imagenet_from_wnids
from .core.datasets.coco import generate_coco_hierarchy
from .core.datasets.coco import generate_coco_hierarchy
from .core.datasets.openimages import generate_openimages_hierarchy
from .core.datasets.tencent import generate_tencent_hierarchy

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


def get_api_key() -> Optional[str]:
    """Get API key from environment or config."""
    if config.api_key:
        return config.api_key
    return os.environ.get('OPENROUTER_API_KEY')


def cmd_dataset_imagenet(args):
    """Handle imagenet subcommand."""
    hierarchy = generate_imagenet_tree(
        root_synset_str=args.root,
        max_depth=args.depth,
        filter_set=args.filter if args.filter != 'none' else None,
        with_glosses=not args.no_glosses,
        strict_filter=not args.no_strict,
        blacklist_abstract=args.blacklist,
        smart=args.smart,
        min_significance_depth=args.min_depth,
        min_hyponyms=args.min_hyponyms,
        min_leaf_size=args.min_leaf,
        merge_orphans=getattr(args, 'merge_orphans', False)
    )
    
    mgr = StructureManager()
    mgr.save_structure(hierarchy, args.output)
    print(f"✓ Saved ImageNet hierarchy to {args.output}")


def cmd_dataset_coco(args):
    """Handle coco subcommand."""
    hierarchy = generate_coco_hierarchy(
        with_glosses=not args.no_glosses,
        max_depth=args.depth
    )
    
    mgr = StructureManager()
    mgr.save_structure(hierarchy, args.output)
    print(f"✓ Saved COCO hierarchy to {args.output}")


def cmd_dataset_openimages(args):
    """Handle openimages subcommand."""
    hierarchy = generate_openimages_hierarchy(
        max_depth=args.depth,
        with_glosses=not args.no_glosses,
        smart=args.smart,
        min_significance_depth=args.min_depth,
        min_hyponyms=args.min_hyponyms,
        min_leaf_size=args.min_leaf,
        merge_orphans=getattr(args, 'merge_orphans', False),
        bbox_only=args.bbox_only
    )
    
    mgr = StructureManager()
    mgr.save_structure(hierarchy, args.output)
    print(f"✓ Saved Open Images hierarchy to {args.output}")


def cmd_dataset_tencent(args):
    """Handle tencent subcommand."""
    hierarchy = generate_tencent_hierarchy(
        max_depth=args.depth,
        with_glosses=not args.no_glosses,
        smart=args.smart,
        min_significance_depth=args.min_depth,
        min_hyponyms=args.min_hyponyms,
        min_leaf_size=args.min_leaf,
        merge_orphans=args.merge_orphans
    )
    
    mgr = StructureManager()
    mgr.save_structure(hierarchy, args.output)
    print(f"✓ Saved Tencent ML-Images hierarchy to {args.output}")


def cmd_categorize(args):
    """Handle categorize command (LLM-powered)."""
    api_key = args.api_key or get_api_key()
    if not api_key:
        print("Error: API key required. Set OPENROUTER_API_KEY or use --api-key")
        sys.exit(1)
    
    from .core.llm import LLMEngine
    
    # Load terms
    with open(args.input, 'r', encoding='utf-8') as f:
        terms = [line.strip() for line in f if line.strip()]
    
    logger.info(f"Loaded {len(terms)} terms from {args.input}")
    
    engine = LLMEngine(api_key=api_key, model=args.model)
    mgr = StructureManager()
    
    # Load existing structure if output exists
    current_structure = mgr.load_structure(args.output) if os.path.exists(args.output) else None
    current_yaml = mgr.to_string(current_structure) if current_structure else ""
    
    # Generate structure
    sample = terms[:50]  # Use sample for structure generation
    structure_yaml = engine.generate_structure(sample, current_yaml)
    
    if not structure_yaml:
        print("Error: Failed to generate structure")
        sys.exit(1)
    
    # Parse the LLM output
    structure = mgr.from_string(structure_yaml)
    
    # Categorize all terms
    categorized = engine.categorize_terms(terms, structure_yaml)
    
    if categorized:
        mgr.merge_categorized_data(structure, categorized)
    
    mgr.save_structure(structure, args.output)
    print(f"✓ Saved categorized hierarchy to {args.output}")


def cmd_create(args):
    """Handle create command (LLM-powered)."""
    api_key = args.api_key or get_api_key()
    if not api_key:
        print("Error: API key required. Set OPENROUTER_API_KEY or use --api-key")
        sys.exit(1)
    
    from .core.llm import LLMEngine
    
    engine = LLMEngine(api_key=api_key, model=args.model)
    mgr = StructureManager()
    
    logger.info(f"Generating taxonomy for topic: {args.topic}")
    
    structure_yaml = engine.generate_dynamic_structure(args.topic)
    
    if not structure_yaml:
        print("Error: Failed to generate structure")
        sys.exit(1)
    
    structure = mgr.from_string(structure_yaml)
    mgr.save_structure(structure, args.output)
    print(f"✓ Saved taxonomy to {args.output}")


def cmd_enrich(args):
    """Handle enrich command (LLM-powered)."""
    api_key = args.api_key or get_api_key()
    if not api_key:
        print("Error: API key required. Set OPENROUTER_API_KEY or use --api-key")
        sys.exit(1)
    
    from .core.llm import LLMEngine
    
    engine = LLMEngine(api_key=api_key, model=args.model)
    mgr = StructureManager()
    
    # Load existing structure
    structure = mgr.load_structure(args.input)
    if not structure:
        print(f"Error: Could not load {args.input}")
        sys.exit(1)
    
    current_yaml = mgr.to_string(structure)
    
    logger.info(f"Enriching instructions in {args.input}")
    
    enriched_yaml = engine.enrich_instructions(current_yaml, args.topic)
    
    if not enriched_yaml:
        print("Error: Failed to enrich structure")
        sys.exit(1)
    
    enriched = mgr.from_string(enriched_yaml)
    output = args.output or args.input
    mgr.save_structure(enriched, output)
    print(f"✓ Saved enriched hierarchy to {output}")


def cmd_gui(args):
    """Handle gui command."""
    from .gui import launch_gui
    launch_gui(share=args.share)


def main():
    parser = argparse.ArgumentParser(
        prog='wildcards-gen',
        description='Generate skeleton YAML files for wildcards'
    )
    subparsers = parser.add_subparsers(dest='command', required=True)
    
    # === DATASET COMMAND ===
    p_dataset = subparsers.add_parser('dataset', help='Generate from CV dataset')
    dataset_sub = p_dataset.add_subparsers(dest='dataset_type', required=True)
    
    def add_smart_args(parser):
        parser.add_argument('--smart', action='store_true', help='Use semantic significance pruning (ignoring --depth)')
        parser.add_argument('--min-depth', type=int, default=6, help='[Smart] Max WordNet depth for significance (lower = more fundamental categories)')
        parser.add_argument('--min-hyponyms', type=int, default=10, help='[Smart] Min descendants to keep as category (higher = fewer, larger categories)')
        parser.add_argument('--min-leaf', type=int, default=3, help='[Smart] Min items per leaf list (smaller lists are merged upward)')
        parser.add_argument('--merge-orphans', action='store_true', help='[Smart] Merge small pruned lists into parent misc category')

    # ImageNet
    p_imagenet = dataset_sub.add_parser('imagenet', help='ImageNet (WordNet-based) hierarchy')
    p_imagenet.add_argument('--root', default=config.get("datasets.imagenet.root_synset"), help='Root synset')
    p_imagenet.add_argument('--depth', type=int, default=config.get("generation.default_depth"), help='Max depth')
    p_imagenet.add_argument('--filter', choices=['1k', '21k', 'none'], default=config.get("datasets.imagenet.filter") or 'none')
    p_imagenet.add_argument('--no-glosses', action='store_true', help='Skip WordNet glosses')
    p_imagenet.add_argument('--no-strict', action='store_true', help='Disable strict filtering')
    p_imagenet.add_argument('--blacklist', action='store_true', help='Blacklist abstract categories')
    add_smart_args(p_imagenet)
    p_imagenet.add_argument('-o', '--output', default=os.path.join(config.output_dir, 'imagenet.yaml'))
    p_imagenet.set_defaults(func=cmd_dataset_imagenet)
    
    # COCO
    p_coco = dataset_sub.add_parser('coco', help='COCO hierarchy')
    p_coco.add_argument('--depth', type=int, default=10)
    p_coco.add_argument('--no-glosses', action='store_true')
    p_coco.add_argument('-o', '--output', default=os.path.join(config.output_dir, 'coco.yaml'))
    p_coco.set_defaults(func=cmd_dataset_coco)
    
    # OpenImages
    p_oi = dataset_sub.add_parser('openimages', help='Open Images hierarchy')
    p_oi.add_argument('--depth', type=int, default=config.get("generation.default_depth"))
    p_oi.add_argument('--no-glosses', action='store_true')
    p_oi.add_argument('--bbox-only', action='store_true', help='Use only the 600 bounding-box labels (default: full 20k labels)')
    add_smart_args(p_oi)
    p_oi.add_argument('-o', '--output', default=os.path.join(config.output_dir, 'openimages.yaml'))
    p_oi.set_defaults(func=cmd_dataset_openimages)

    # Tencent
    p_tencent = dataset_sub.add_parser('tencent', help='Tencent ML-Images hierarchy')
    p_tencent.add_argument('--depth', type=int, default=config.get("generation.default_depth"), help='Max depth (ignored if --smart)')
    p_tencent.add_argument('--no-glosses', action='store_true', help='Skip WordNet glosses')
    add_smart_args(p_tencent)
    p_tencent.add_argument('-o', '--output', default=os.path.join(config.output_dir, 'tencent.yaml'))
    p_tencent.set_defaults(func=cmd_dataset_tencent)
    
    # === CATEGORIZE COMMAND ===
    p_cat = subparsers.add_parser('categorize', help='Categorize flat term list (LLM)')
    p_cat.add_argument('input', help='Input text file with terms')
    p_cat.add_argument('-o', '--output', default=os.path.join(config.output_dir, 'categorized.yaml'))
    p_cat.add_argument('--api-key', help='OpenRouter API key')
    p_cat.add_argument('--model', default=config.model)
    p_cat.set_defaults(func=cmd_categorize)
    
    # === CREATE COMMAND ===
    p_create = subparsers.add_parser('create', help='Generate taxonomy for topic (LLM)')
    p_create.add_argument('--topic', required=True, help='Topic for taxonomy')
    p_create.add_argument('-o', '--output', default=os.path.join(config.output_dir, 'taxonomy.yaml'))
    p_create.add_argument('--api-key', help='OpenRouter API key')
    p_create.add_argument('--model', default=config.model)
    p_create.set_defaults(func=cmd_create)
    
    # === ENRICH COMMAND ===
    p_enrich = subparsers.add_parser('enrich', help='Add/improve instructions (LLM)')
    p_enrich.add_argument('input', help='Input YAML file')
    p_enrich.add_argument('-o', '--output', help='Output file (default: overwrite input)')
    p_enrich.add_argument('--topic', default='AI image generation wildcards')
    p_enrich.add_argument('--api-key', help='OpenRouter API key')
    p_enrich.add_argument('--model', default=config.model)
    p_enrich.set_defaults(func=cmd_enrich)
    
    # === GUI COMMAND ===
    p_gui = subparsers.add_parser('gui', help='Launch Gradio GUI')
    p_gui.add_argument('--share', action='store_true', default=config.get("gui.share"), help='Create public link')
    p_gui.add_argument('--port', type=int, default=config.get("gui.server_port"))
    p_gui.set_defaults(func=cmd_gui)
    
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
