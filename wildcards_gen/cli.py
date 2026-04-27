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
import yaml
from typing import Optional

from .core.config import config
from .core.structure import StructureManager
from .core.stats import StatsCollector
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

# Silence only the most verbose network/API loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
# Keep lifecycle logs (model loading, etc.) visible
logging.getLogger("sentence_transformers").setLevel(logging.INFO)


def get_api_key() -> Optional[str]:
    """Get API key from environment or config."""
    if config.api_key:
        return config.api_key
    return os.environ.get('OPENROUTER_API_KEY')
from .core.presets import SMART_PRESETS, DATASET_PRESET_OVERRIDES, DATASET_CATEGORY_OVERRIDES
from .core.smart import SmartConfig
from .core.builder import HierarchyBuilder

def resolve_output_path(path: str) -> str:
    """Ensure path is in output_dir if no directory is specified."""
    if os.path.dirname(path):
        return path
    return os.path.join(config.output_dir, path)
def apply_smart_preset(args):
    """Apply preset values to args, with explicit flags taking precedence."""
    preset_name = getattr(args, 'preset', None)
    
    # Map CLI lowercase to Preset TitleCase
    # (min_depth, min_hyponyms, min_leaf, merge_orphans)
    preset_map = {k.lower(): v for k, v in SMART_PRESETS.items()}
    
    # Determine defaults (check overrides first)
    defaults = preset_map['balanced']
    dataset_type = getattr(args, 'dataset_type', None)
    
    # Map CLI dataset to Preset dataset name
    ds_map = {
        "openimages": "Open Images",
        "tencent": "Tencent ML-Images",
        "imagenet": "ImageNet"
    }
    ds_key = ds_map.get(dataset_type)
    
    if preset_name:
        preset_key = preset_name.lower()
        # Check overrides
        if ds_key and ds_key in DATASET_PRESET_OVERRIDES:
            overrides = {k.lower(): v for k, v in DATASET_PRESET_OVERRIDES[ds_key].items()}
            if preset_key in overrides:
                defaults = overrides[preset_key]
            else:
                defaults = preset_map.get(preset_key, defaults)
        else:
            defaults = preset_map.get(preset_key, defaults)
    
    if getattr(args, 'min_depth', None) is None:
        args.min_depth = defaults[0]
    if getattr(args, 'min_hyponyms', None) is None:
        args.min_hyponyms = defaults[1]
    if getattr(args, 'min_leaf', None) is None:
        args.min_leaf = defaults[2]
    if getattr(args, 'merge_orphans', None) is None:
        args.merge_orphans = defaults[3]


def load_smart_overrides(config_path: Optional[str]) -> dict:
    """Load smart overrides from a YAML file."""
    if not config_path:
        return {}
    
    if not os.path.exists(config_path):
        logger.warning(f"Smart config file not found: {config_path}")
        return {}
        
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            if not isinstance(data, dict):
                logger.warning(f"Invalid smart config format in {config_path} (expected dict)")
                return {}
            return data
    except Exception as e:
        logger.error(f"Failed to load smart config: {e}")
        return {}


def get_smart_config(args, dataset_name: Optional[str] = None) -> SmartConfig:
    """Helper to build SmartConfig from CLI args."""
    apply_smart_preset(args)
    overrides = load_smart_overrides(args.smart_config)
    
    # Merge with dataset-specific presets if available
    preset_overrides = DATASET_CATEGORY_OVERRIDES.get(dataset_name, {}) if dataset_name else {}
    final_overrides = preset_overrides.copy()
    if overrides:
        final_overrides.update(overrides)
        
    return SmartConfig(
        enabled=args.smart,
        min_depth=args.min_depth,
        min_hyponyms=args.min_hyponyms,
        min_leaf_size=args.min_leaf,
        merge_orphans=getattr(args, 'merge_orphans', False),
        category_overrides=final_overrides,
        semantic_cleanup=args.semantic_clean,
        semantic_model=args.semantic_model,
        semantic_threshold=args.semantic_threshold,
        semantic_arrangement=args.semantic_arrange,
        semantic_arrangement_threshold=args.semantic_arrange_threshold,
        semantic_arrangement_min_cluster=args.semantic_arrange_min_cluster,
        semantic_arrangement_method=args.semantic_arrange_method,
        debug_arrangement=args.debug_arrangement,
        skip_nodes=args.skip_nodes,
        orphans_label_template=args.orphans_label_template
    )


def cmd_dataset_imagenet(args):
    """Handle imagenet subcommand."""
    # Analysis mode override
    if getattr(args, 'analyze', False):
        print("🔍 Analyzing ImageNet hierarchy... (this may take a moment)")
        tree = generate_imagenet_tree(
            root_synset_str=args.root,
            max_depth=max(args.depth, 10),
            filter_set=args.filter if args.filter != 'none' else None,
            with_glosses=False,
            strict_filter=not args.no_strict,
            blacklist_abstract=args.blacklist
        )
        if not tree: return
        
        # Temporary conversion to CommentedMap for analyzer
        builder = HierarchyBuilder(SmartConfig(enabled=False))
        hierarchy = builder._to_commented_map(tree)
        
        from .core import analyze
        stats_data = analyze.compute_dataset_stats(hierarchy)
        suggestions = analyze.suggest_thresholds(stats_data)
        analyze.print_analysis_report(stats_data, suggestions)
        return

    smart_config = get_smart_config(args, "ImageNet")
    
    # Initialize stats
    stats = StatsCollector()
    stats.set_metadata("dataset", "imagenet")
    stats.set_metadata("output", args.output)
    stats.set_metadata("smart_config", smart_config.to_dict())

    # 1. Extraction (Raw Tree)
    tree = generate_imagenet_tree(
        root_synset_str=args.root,
        max_depth=args.depth,
        filter_set=args.filter if args.filter != 'none' else None,
        with_glosses=not args.no_glosses,
        strict_filter=not args.no_strict,
        blacklist_abstract=args.blacklist,
        exclude_regex=args.exclude_regex,
        exclude_subtree=args.exclude_subtree
    )
    
    if not tree:
        print("Error: Failed to extract ImageNet tree")
        return

    # 2. Build (Smart Processing)
    if smart_config.enabled:
        builder = HierarchyBuilder(smart_config, stats=stats)
        hierarchy = builder.build(tree)
    else:
        # Simple depth-based conversion
        builder = HierarchyBuilder(smart_config)
        hierarchy = builder._to_commented_map(tree)
        # Ensure it's wrapped in root name if not already
        if tree.name not in hierarchy:
            from ruamel.yaml.comments import CommentedMap
            res = CommentedMap()
            res[tree.name] = hierarchy
            hierarchy = res
    
    output_path = resolve_output_path(args.output)
    mgr = StructureManager()
    mgr.save_structure(hierarchy, output_path, format=args.format)
    
    # Save stats
    if config.get("generation.save_stats"):
        filename = os.path.basename(output_path)
        stem = os.path.splitext(filename)[0]
        base_path = os.path.join(config.output_dir, stem)
        os.makedirs(config.output_dir, exist_ok=True)
        stats.save_to_json(f"{base_path}.stats.json")
        stats.save_summary_log(f"{base_path}.log")
        print(f"✓ Saved generation logs to {base_path}.log")


def cmd_dataset_coco(args):
    """Handle coco subcommand."""
    hierarchy = generate_coco_hierarchy(
        with_glosses=not args.no_glosses,
        max_depth=args.depth
    )
    
    mgr = StructureManager()
    mgr.save_structure(hierarchy, args.output, format=args.format)
    print(f"✓ Saved COCO hierarchy to {args.output}")


def cmd_dataset_openimages(args):
    """Handle openimages subcommand."""
    # Analysis mode override
    if getattr(args, 'analyze', False):
        print("🔍 Analyzing Open Images hierarchy...")
        tree = generate_openimages_hierarchy(
            max_depth=max(args.depth, 10),
            with_glosses=False,
            bbox_only=args.bbox_only
        )
        if not tree: return
        builder = HierarchyBuilder(SmartConfig(enabled=False))
        hierarchy = builder._to_commented_map(tree)
        from .core import analyze
        stats = analyze.compute_dataset_stats(hierarchy)
        suggestions = analyze.suggest_thresholds(stats)
        analyze.print_analysis_report(stats, suggestions)
        return

    smart_config = get_smart_config(args, "Open Images")
    
    # Initialize stats
    stats = StatsCollector()
    stats.set_metadata("dataset", "openimages")
    stats.set_metadata("output", args.output)
    stats.set_metadata("smart_config", smart_config.to_dict())

    # 1. Extraction
    tree = generate_openimages_hierarchy(
        max_depth=args.depth,
        with_glosses=not args.no_glosses,
        bbox_only=args.bbox_only
    )
    
    if not tree:
        print("Error: Failed to extract Open Images tree")
        return

    # 2. Build
    if smart_config.enabled:
        builder = HierarchyBuilder(smart_config, stats=stats)
        hierarchy = builder.build(tree)
    else:
        builder = HierarchyBuilder(smart_config)
        hierarchy = builder._to_commented_map(tree)
        if tree.name not in hierarchy:
            from ruamel.yaml.comments import CommentedMap
            res = CommentedMap()
            res[tree.name] = hierarchy
            hierarchy = res
    
    output_path = resolve_output_path(args.output)
    mgr = StructureManager()
    mgr.save_structure(hierarchy, output_path, format=args.format)
    
    # Save stats
    if config.get("generation.save_stats"):
        filename = os.path.basename(output_path)
        stem = os.path.splitext(filename)[0]
        base_path = os.path.join(config.output_dir, stem)
        os.makedirs(config.output_dir, exist_ok=True)
        stats.save_to_json(f"{base_path}.stats.json")
        stats.save_summary_log(f"{base_path}.log")
        print(f"✓ Saved generation logs to {base_path}.log")


def cmd_dataset_tencent(args):
    """Handle tencent subcommand."""
    # Analysis mode override
    if getattr(args, 'analyze', False):
        print("🔍 Analyzing Tencent ML-Images hierarchy...")
        tree = generate_tencent_hierarchy(
            max_depth=max(args.depth, 10),
            with_glosses=False
        )
        if not tree: return
        builder = HierarchyBuilder(SmartConfig(enabled=False))
        hierarchy = builder._to_commented_map(tree)
        from .core import analyze
        stats_data = analyze.compute_dataset_stats(hierarchy)
        suggestions = analyze.suggest_thresholds(stats_data)
        analyze.print_analysis_report(stats_data, suggestions)
        return

    smart_config = get_smart_config(args, "Tencent ML-Images")
    
    # Initialize stats
    stats = StatsCollector()
    stats.set_metadata("dataset", "tencent")
    stats.set_metadata("output", args.output)
    stats.set_metadata("smart_config", smart_config.to_dict())

    # 1. Extraction
    tree = generate_tencent_hierarchy(
        max_depth=args.depth,
        with_glosses=not args.no_glosses
    )
    
    if not tree:
        print("Error: Failed to extract Tencent tree")
        return

    # 2. Build
    if smart_config.enabled:
        builder = HierarchyBuilder(smart_config, stats=stats)
        hierarchy = builder.build(tree)
    else:
        builder = HierarchyBuilder(smart_config)
        hierarchy = builder._to_commented_map(tree)
        if tree.name not in hierarchy:
            from ruamel.yaml.comments import CommentedMap
            res = CommentedMap()
            res[tree.name] = hierarchy
            hierarchy = res
    
    output_path = resolve_output_path(args.output)
    mgr = StructureManager()
    mgr.save_structure(hierarchy, output_path, format=args.format)
    print(f"✓ Saved Tencent ML-Images hierarchy to {output_path}")

    # Save stats
    if config.get("generation.save_stats"):
        filename = os.path.basename(output_path)
        stem = os.path.splitext(filename)[0]
        base_path = os.path.join(config.output_dir, stem)
        os.makedirs(config.output_dir, exist_ok=True)
        stats.save_to_json(f"{base_path}.stats.json")
        stats.save_summary_log(f"{base_path}.log")
        print(f"✓ Saved generation logs to {base_path}.log")


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


def cmd_batch(args):
    """Handle batch command."""
    from .batch import BatchProcessor
    
    if not os.path.exists(args.manifest):
        print(f"Error: Manifest file not found: {args.manifest}")
        sys.exit(1)
        
    processor = BatchProcessor(args.manifest, workers=args.workers)
    processor.run()


def cmd_gui(args):
    """Handle gui command."""
    from .gui import launch_gui
    launch_gui(share=args.share, port=args.port)


def cmd_lint(args):
    """
    lint <file> [--model=qwen3] [--threshold=0.1] [--clean]
        Check for semantic outliers using embedding models.
        Strategies:
         --clean: Remove outliers and save to new file.
    """
    from wildcards_gen.core.linter import lint_file, print_lint_report, clean_structure, check_dependencies
    from pathlib import Path

    file_path = args.file
    model_name = args.model or "qwen3"
    threshold = float(args.threshold) if args.threshold else 0.1
    do_clean = args.clean

    if not check_dependencies():
         print("❌ Linting requires extra dependencies.")
         print("   Run: pip install wildcards-gen[lint]")
         return

    print(f"🔍 Linting {file_path} with {model_name} (threshold={threshold})...")
    
    try:
        report, structure = lint_file(file_path, model_name, threshold)
        print_lint_report(report)
        
        if do_clean and report['issues']:
            print("\n🧹 Cleaning structure...")
            clean_data = clean_structure(structure, report)
            
            # Save to new file
            p = Path(file_path)
            raw_new_path = f"{p.stem}_clean{p.suffix}"
            new_path = resolve_output_path(raw_new_path)
            
            from wildcards_gen.core.structure import StructureManager
            mgr = StructureManager()
            mgr.save_structure(clean_data, str(new_path))
            print(f"✅ Cleaned file saved to: {new_path}")
            
    except ImportError as e:
        print(f"❌ Dependency Error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

def cmd_compare(args):
    """
    compare <file1> <file2>
        Compare two wildcard files for content and structural stability.
        Metrics:
          - Jaccard Index: Content overlap (1.0 = identical terms).
          - ARI: Clustering similarity (1.0 = identical grouping).
    """
    from wildcards_gen.analytics.metrics import check_dependencies
    
    if not check_dependencies():
         print("❌ Analysis requires extra dependencies.")
         print("   Run: pip install wildcards-gen[lint]")
         return

    from wildcards_gen.analytics.comparator import TaxonomyComparator
    
    file1 = args.file
    # Access the second positional argument which we'll need to add to the parser
    file2 = args.other_file 

    print(f"📊 Comparing:\n  A: {file1}\n  B: {file2}")
    
    try:
        comp = TaxonomyComparator()
        result = comp.compare(file1, file2)
        metrics = result['metrics']
        
        print("\nStability Report")
        print("================")
        print(f"Content Stability (Jaccard):   {metrics['jaccard_content']:.4f}")
        print(f"Structure Stability (ARI):     {metrics['adjusted_rand_index']:.4f}")
        print(f"Common Terms:                  {metrics['common_terms_count']}")
        print(f"Total Unique Terms:            {metrics['union_terms_count']}")
        print("================")

    except Exception as e:
        print(f"❌ Error during comparison: {e}")


def main():
    parser = argparse.ArgumentParser(
        prog='wildcards-gen',
        description='Generate skeleton YAML files for wildcards'
    )
    subparsers = parser.add_subparsers(dest='command', required=True)
    
    # === DATASET COMMAND ===
    p_dataset = subparsers.add_parser('dataset', help='Generate from CV dataset')
    dataset_sub = p_dataset.add_subparsers(dest='dataset_type', required=True)
    
    from .core import analyze

    def add_smart_args(parser):
        parser.add_argument('--smart', action='store_true', help='Use semantic significance pruning (ignoring --depth)')
        parser.add_argument('--analyze', action='store_true', help='Dry-run: Analyze logical structure and suggest smart thresholds')
        parser.add_argument('--preset', choices=[k.lower() for k in SMART_PRESETS.keys()], default=None,
                            help='Smart tuning preset (sets defaults for other smart args)')
        parser.add_argument('--min-depth', type=int, default=None, help='[Smart] Max WordNet depth for significance (lower = more fundamental categories)')
        parser.add_argument('--min-hyponyms', type=int, default=None, help='[Smart] Min descendants to keep as category (higher = fewer, larger categories)')
        parser.add_argument('--min-leaf', type=int, default=None, help='[Smart] Min items per leaf list (smaller lists are merged upward)')
        parser.add_argument('--merge-orphans', action='store_true', default=None, help='[Smart] Merge small pruned lists into parent misc category')
        parser.add_argument('--smart-config', type=str, default=None, help='[Smart] Path to YAML config file for fine-grained per-category overrides')
        # Semantic cleaning args
        parser.add_argument('--semantic-clean', action='store_true', help='[Smart] Enable semantic outlier removal from leaf lists using embeddings')
        parser.add_argument('--semantic-model', choices=['minilm', 'mpnet', 'qwen3'], default='minilm', help='[Smart] Model for semantic cleaning (default: minilm)')
        parser.add_argument('--semantic-threshold', type=float, default=0.1, help='[Smart] Outlier detection threshold')
        # Semantic Arrangement
        parser.add_argument('--semantic-arrange', action='store_true', help='[Smart] Enable semantic arrangement (re-grouping) of flattened lists')
        parser.add_argument('--semantic-arrange-threshold', type=float, default=0.3, help='[Smart] Cluster acceptance probability (0-1, higher=stricter) for arrangement')
        parser.add_argument('--semantic-arrange-min-cluster', type=int, default=5, help='[Smart] Minimum items to form a named cluster')
        parser.add_argument('--semantic-arrange-method', choices=['eom', 'leaf'], default='eom', help='[Smart] Clustering method: eom (stable) or leaf (granular)')
        parser.add_argument('--debug-arrangement', action='store_true', help='[Smart] Show arrangement stats')
        parser.add_argument('--skip-nodes', nargs='+', help='[Smart] Nodes (WNID or name) to structurally skip (elide) while promoting children')
        parser.add_argument('--orphans-label-template', type=str, default=None, help='[Smart] Template for orphan categories (e.g. "other_{}")')
        # Format
        parser.add_argument('--format', choices=['yaml', 'jsonl'], default=None, help='Output format (yaml/jsonl). Defaults to yaml unless output ext is .jsonl')

    # ImageNet
    p_imagenet = dataset_sub.add_parser('imagenet', help='ImageNet (WordNet-based) hierarchy')
    p_imagenet.add_argument('--root', default=config.get("datasets.imagenet.root_synset"), help='Root synset')
    p_imagenet.add_argument('--depth', type=int, default=config.get("generation.default_depth"), help='Max depth')
    p_imagenet.add_argument('--filter', choices=['1k', '21k', 'none'], default=config.get("datasets.imagenet.filter") or 'none')
    p_imagenet.add_argument('--no-glosses', action='store_true', help='Skip WordNet glosses')
    p_imagenet.add_argument('--no-strict', action='store_true', help='Disable strict filtering')
    p_imagenet.add_argument('--blacklist', action='store_true', help='Blacklist abstract categories')
    p_imagenet.add_argument('--exclude-regex', nargs='+', help='Regex patterns to exclude (e.g. ".*sex.*" ".*nudity.*"')
    p_imagenet.add_argument('--exclude-subtree', nargs='+', help='Subtree root WNIDs/names to exclude (e.g. "n02121808" "feline")')
    add_smart_args(p_imagenet)
    p_imagenet.add_argument('-o', '--output', default=os.path.join(config.output_dir, 'imagenet.yaml'))
    p_imagenet.set_defaults(func=cmd_dataset_imagenet)
    
    # COCO
    p_coco = dataset_sub.add_parser('coco', help='COCO hierarchy')
    p_coco.add_argument('--depth', type=int, default=10)
    p_coco.add_argument('--no-glosses', action='store_true')
    p_coco.add_argument('-o', '--output', default=os.path.join(config.output_dir, 'coco.yaml'))
    p_coco.add_argument('--format', choices=['yaml', 'jsonl'], default=None, help='Output format (yaml/jsonl)')
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

    # === LINT COMMAND ===
    p_lint = subparsers.add_parser('lint', help='Analyze skeleton for semantic quality')
    p_lint.add_argument('file', type=str, help='Path to skeleton YAML file')
    p_lint.add_argument('--model', choices=['qwen3', 'mpnet', 'minilm'], default='qwen3',
                        help='Embedding model (qwen3=best quality, minilm=fastest)')
    p_lint.add_argument('--threshold', type=float, default=0.1,
                        help='HDBSCAN outlier score threshold (0-1, higher = stricter)')
    p_lint.add_argument('--clean', action='store_true', help='Remove outliers and save to new file.')
    p_lint.add_argument('--output', choices=['json', 'markdown'], default='markdown')
    p_lint.set_defaults(func=cmd_lint)

    # === COMPARE COMMAND ===
    p_comp = subparsers.add_parser('compare', help='Compare two wildcard files for stability.')
    p_comp.add_argument('file', help='First file path')
    p_comp.add_argument('other_file', help='Second file path')
    p_comp.set_defaults(func=cmd_compare)
    
    # === BATCH COMMAND ===
    p_batch = subparsers.add_parser('batch', help='Run batch generation jobs from manifest')
    p_batch.add_argument('manifest', help='Path to YAML manifest file')
    p_batch.add_argument('--workers', type=int, default=1, help='Number of parallel workers')
    p_batch.set_defaults(func=cmd_batch)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()