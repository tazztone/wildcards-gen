import gradio as gr
import os
import yaml
import logging
import datetime
from nltk.corpus import wordnet as wn

# Local Imports
from wildcards_gen.core.datasets import imagenet, coco, openimages, tencent
from wildcards_gen.core.structure import StructureManager
from wildcards_gen.core.config import config
from wildcards_gen.core.llm import LLMEngine
from wildcards_gen.core.stats import StatsCollector
from .core.presets import SMART_PRESETS, DATASET_PRESET_OVERRIDES

# =============================================================================
# 1. SETUP & LOGGING
# =============================================================================
logger = logging.getLogger(__name__)

# Load Custom CSS
CSS_PATH = os.path.join(os.path.dirname(__file__), 'custom.css')
with open(CSS_PATH, 'r') as f:
    CUSTOM_CSS = f.read()

# =============================================================================
# 2. CONSTANTS
# =============================================================================
# Defined at module level to be shared by multiple UI components
COMMON_ROOTS = {
    '— General —': '',
    'Everything (Entity)': 'entity.n.01',
    'Physical Objects': 'physical_entity.n.01',
    
    '— Living —': '',
    'Animals': 'animal.n.01',
    'Plants': 'plant.n.02',
    'People': 'person.n.01',
    'Body Parts': 'body_part.n.01',
    
    '— Artifacts —': '',
    'Artifacts (All)': 'artifact.n.01',
    'Structures & Buildings': 'structure.n.01',
    'Vehicles': 'vehicle.n.01',
    'Tools': 'tool.n.01',
    'Instrumentation': 'instrumentality.n.03',
    'Furniture': 'furniture.n.01',
    'Clothing': 'clothing.n.01',
    'Food': 'food.n.01',
    'Containers': 'container.n.01',
    'Devices': 'device.n.01',
    'Equipment': 'equipment.n.01',
    'Decorations': 'decoration.n.01',
    'Fabrics': 'fabric.n.01',
    
    '— Nature —': '',
    'Natural Objects': 'natural_object.n.01',
    'Geological Formations': 'geological_formation.n.01',
    'Substances': 'substance.n.01',
    
    '— Concepts —': '',
    'Locations': 'location.n.01',
    'Events': 'event.n.01',
    'Groups': 'group.n.01',
    'Phenomena': 'phenomenon.n.01',
    'Communication': 'communication.n.02'
}

# =============================================================================
# 3. UTILITY FUNCTIONS (PURE & FORMATTING)
# =============================================================================
def clean_filename(s):
    """Clean string for use in filename."""
    import re
    s = s.lower().replace(' ', '_')
    return re.sub(r'[^a-z0-9_.]', '', s)

def update_ds_filename(name, root, depth, strategy, min_depth=4, min_hyponyms=50, min_leaf=5, bbox_only=False):
    # Only use root in filename if it's ImageNet, otherwise ignore the hidden input
    root_part = ''
    if name == 'ImageNet':
        root_part = clean_filename(root.split('.')[0]) if '.' in root else clean_filename(root)
    
    name_part = clean_filename(name)
    strategy_suffix = '_smart' if strategy == 'Smart' else ''
    bbox_suffix = '_bbox' if (bbox_only and name == 'Open Images') else ''
    
    components = [name_part]
    if root_part: components.append(root_part)
    components.append(f'd{depth}')
    
    if strategy == 'Smart':
        components.append(f's{min_depth}')
        components.append(f'f{min_hyponyms}')
        components.append(f'l{min_leaf}')
        components.append('smart')
    
    if bbox_suffix: components.append(bbox_suffix.strip('_'))
    
    return '_'.join(components) + '.yaml'

def update_cr_filename(topic):
    if not topic: return 'topic_skeleton.yaml'
    return f'{clean_filename(topic)[:30]}_skeleton.yaml'

def update_cat_filename(terms):
    if not terms: return 'categorized.yaml'
    first_term = terms.split('\n')[0][:20]
    return f'categorized_{clean_filename(first_term)}.yaml'

def update_en_filename(topic):
    if not topic: return 'enriched.yaml'
    return f'enriched_{clean_filename(topic)[:20]}.yaml'

# =============================================================================
# 4. LOGIC HELPERS (IO & STATE)
# =============================================================================
def save_and_preview(data, output_name):
    """Helper to save structure and return path + content."""
    mgr = StructureManager()
    yaml_str = mgr.to_string(data)
    
    output_dir = config.output_dir
    os.makedirs(output_dir, exist_ok=True)
    if not output_name.endswith('.yaml'):
        output_name += '.yaml'
    output_path = os.path.join(output_dir, output_name)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(yaml_str)
        
    # Truncate for preview to avoid UI lag
    lines = yaml_str.split('\n')
    if len(lines) > 500:
        preview_str = '\n'.join(lines[:500]) + '\n\n# ... (Preview truncated. Download file to view full content.)'
    else:
        preview_str = yaml_str

    return output_path, preview_str

def search_wordnet(query):
    """Search for synsets matching the query."""
    if not query or len(query) < 2:
        return 'Please enter at least 2 characters.'
    
    try:
        synsets = wn.synsets(query.replace(' ', '_'))
        if not synsets:
            return f"No results found for '{query}'."
        
        results = []
        for s in synsets:
            wnid = f'{s.pos()}{s.offset():08d}'
            results.append(f'**{s.name()}** (`{wnid}`)\n_{s.definition()}_\n')
            
        return '\n'.join(results)
    except Exception as e:
        return f'Error: {str(e)}'

def update_ds_ui(dataset_name, strategy):
    """Calculate visibility and state updates for dataset-related UI components."""
    is_imagenet = (dataset_name == 'ImageNet')
    can_use_smart = dataset_name in ['ImageNet', 'Open Images', 'Tencent ML-Images']
    is_smart = (strategy == 'Smart') and can_use_smart
    new_strategy = 'Smart' if (can_use_smart and dataset_name != 'COCO') else strategy
    
    return [
        gr.update(visible=is_imagenet),                # ds_imagenet_group
        gr.update(interactive=can_use_smart, value=new_strategy if not can_use_smart else strategy), # ds_strategy
        gr.update(visible=is_smart),                   # smart_tuning_group
        gr.update(visible=is_imagenet),                # adv_filter_group
        gr.update(visible=(dataset_name == 'Open Images')), # ds_openimages_group
    ]

# =============================================================================
# 5. EVENT HANDLERS
# =============================================================================
def on_dataset_change(dataset_name, strategy):
    """Handle all UI updates when the source dataset or extraction mode changes."""
    # 1. Run the existing UI visibility logic
    visibility_updates = update_ds_ui(dataset_name, strategy)
    
    # 2. Update the info markdown
    info_text = {
        'ImageNet': '_**ImageNet**: 21k classes. Best for general objects/animals._',
        'COCO': '_**COCO**: 80 objects. Very small, flat list._',
        'Open Images': '_**Open Images V7**: ~600 bbox classes or 20k+ image labels._',
        'Tencent ML-Images': '_**Tencent ML**: 11k categories. Massive, modern coverage._'
    }.get(dataset_name, '')
    
    # Returns: visibility_updates (5) + info_update (1)
    return visibility_updates + [
        gr.update(value=info_text)
    ]

def generate_dataset_handler(
    dataset_name, strategy, root, depth, output_name,
    with_glosses, filter_set, strict_filter, blacklist_abstract,
    min_depth, min_hyponyms, min_leaf, merge_orphans,
    bbox_only,
    semantic_clean, semantic_model, semantic_threshold,
    semantic_arrange, semantic_arrange_threshold, semantic_arrange_min_cluster,
    exclude_subtree=None, exclude_regex=None,
    semantic_arrange_method='eom', debug_arrangement=False,
    umap_neighbors=15, umap_dist=0.1, min_samples=5, orphans_template="misc",
    fast_preview=False,
    progress=gr.Progress()
):
    progress(0, desc='Initializing...')
    try:
        is_smart = (strategy == 'Smart')
        
        # Initialize Stats Collector
        stats = StatsCollector()
        stats.set_metadata("dataset", dataset_name)
        stats.set_metadata("output", output_name)
        stats.set_metadata("fast_preview", fast_preview)

        if fast_preview:
             limit = config.get('generation.preview_limit', 500)
             preview_limit = int(limit)
        else:
             preview_limit = None
        
        # Common kwargs for smart datasets
        smart_kwargs = {'stats': stats} # Always pass stats if available
        if is_smart:
            smart_kwargs.update({
                'smart': True,
                'min_significance_depth': int(min_depth),
                'min_hyponyms': int(min_hyponyms),
                'min_leaf_size': int(min_leaf),
                'merge_orphans': merge_orphans,
                'semantic_cleanup': semantic_clean,
                'semantic_model': semantic_model,
                'semantic_threshold': float(semantic_threshold),
                'semantic_arrangement': semantic_arrange,
                'semantic_arrangement_threshold': float(semantic_arrange_threshold),
                'semantic_arrangement_min_cluster': int(semantic_arrange_min_cluster),
                'semantic_arrangement_method': semantic_arrange_method,
                'debug_arrangement': debug_arrangement,
                'preview_limit': preview_limit,
                'umap_n_neighbors': int(umap_neighbors),
                'umap_min_dist': float(umap_dist),
                'hdbscan_min_samples': int(min_samples),
                'orphans_label_template': orphans_template
            })

        if dataset_name == 'ImageNet':
            if not root:
                return None, 'Error: Root synset required for ImageNet (e.g. entity.n.01)'
            progress(0.2, desc='Downloading ImageNet metadata...')
            
            kwargs = {
                'root_synset_str': root,
                'max_depth': int(depth),
                'filter_set': filter_set if filter_set != 'none' else None,
                'with_glosses': with_glosses,
                'strict_filter': strict_filter,
                'blacklist_abstract': blacklist_abstract,
                'exclude_regex': exclude_regex,
                'exclude_subtree': exclude_subtree,
                'smart': is_smart
            }
            if is_smart:
                kwargs.update(smart_kwargs)
            
            data = imagenet.generate_imagenet_tree(**kwargs)
            
        elif dataset_name == 'COCO':
            progress(0.2, desc='Loading COCO API...')
            data = coco.generate_coco_hierarchy(
                with_glosses=with_glosses
            )
        elif dataset_name == 'Open Images':
            progress(0.2, desc='Loading Open Images metadata...')
            kwargs = {
                'max_depth': int(depth),
                'with_glosses': with_glosses,
                'smart': is_smart,
                'bbox_only': bbox_only,
                'progress_callback': progress
            }
            if is_smart:
                kwargs.update(smart_kwargs)
                
            data = openimages.generate_openimages_hierarchy(**kwargs)
            
        elif dataset_name == 'Tencent ML-Images':
            progress(0.2, desc='Loading Tencent dictionary...')
            kwargs = {
                'max_depth': int(depth),
                'with_glosses': with_glosses,
                'smart': is_smart
            }
            if is_smart:
                kwargs.update(smart_kwargs)
                
            data = tencent.generate_tencent_hierarchy(**kwargs)
        output_path, preview = save_and_preview(data, output_name)
        
        # Save Stats
        if config.get("generation.save_stats"):
            # Always save stats to the configured output directory
            filename = os.path.basename(output_path)
            stem = os.path.splitext(filename)[0]
            base_path = os.path.join(config.output_dir, stem)
            os.makedirs(config.output_dir, exist_ok=True)
            
            stats.save_to_json(f"{base_path}.stats.json")
            stats.save_summary_log(f"{base_path}.log")
        
        # No summary markdown anymore, just duration and status
        summary_md = f"### ✅ Generation Complete\n"
        summary_md += f"* **Total Duration**: {stats.to_dict()['execution']['duration_seconds']}s\n"
        
        # Check for limit reached
        limit_events = [e for e in stats.events if e.event_type == 'limit_reached']
        if limit_events:
             limit_val = limit_events[0].data.get('limit', 500)
             summary_md += f"\n> [!WARNING]\n> **Fast Preview Limit Reached**\n> Processed {limit_val} items. Output is truncated."
        
        # Return summary and list of files [yaml, log, json]
        log_path = f"{base_path}.log"
        json_path = f"{base_path}.stats.json"
        
        return preview, summary_md, [output_path, log_path, json_path]
    except Exception as e:
        logger.exception('Dataset generation failed')
        return f'Error: {str(e)}', '', []

def live_preview_handler(*args):
    """Wrapper for auto-generation that only fires if Fast Preview is checked."""
    # Robust argument handling: Look for boolean at end, or scan args
    # args structure matches all_gen_inputs order
    # fast_preview is the last component in all_gen_inputs
    
    try:
        is_fast_preview = bool(args[-1])
    except:
        is_fast_preview = False

    if not is_fast_preview:
        return gr.update(), gr.update(), gr.update()
    
    # Call the main handler but suppress error spam in preview
    try:
        preview, summary_md, _ = generate_dataset_handler(*args)
        return preview, summary_md, gr.update()
    except Exception as e:
        # Don't break the UI, just show nothing or a subtle message
        return f"# Error during preview: {str(e)}", "", gr.update()

def analyze_handler(
    dataset_name, root, depth, filter_set, strict_filter, blacklist_abstract, bbox_only,
    history,
    progress=gr.Progress()
):
    """Run dry-run analysis and return report + suggestions."""
    progress(0, desc='Analyzing structure...')
    try:
        data = None
        if dataset_name == 'ImageNet':
            if not root: return 'Error: Root required', 4, 50, 5, history, gr.update(visible=False)
            # Force non-smart for analysis
            data = imagenet.generate_imagenet_tree(
                root, max_depth=max(int(depth), 10), filter_set=filter_set if filter_set != 'none' else None,
                with_glosses=False, strict_filter=strict_filter, blacklist_abstract=blacklist_abstract,
                smart=False
            )
        elif dataset_name == 'Open Images':
            # OpenImages needs smart=True but permissive to see structure
            data = openimages.generate_openimages_hierarchy(
                max_depth=max(int(depth), 10), with_glosses=False, smart=True,
                min_significance_depth=20, min_hyponyms=0, min_leaf_size=0, bbox_only=bbox_only
            )
        elif dataset_name == 'Tencent ML-Images':
            data = tencent.generate_tencent_hierarchy(
                max_depth=max(int(depth), 10), with_glosses=False, smart=True,
                min_significance_depth=20, min_hyponyms=0, min_leaf_size=0
            )
        else:
            return 'Analysis not supported for this dataset.', 4, 50, 5, history, gr.update(visible=False)
            
        from wildcards_gen.core import analyze
        stats = analyze.compute_dataset_stats(data)
        tuned = analyze.suggest_thresholds(stats)
        
        report = f'''
### 📊 Analysis Report
* **Max Depth**: {stats.max_depth}
* **Total Nodes**: {stats.total_nodes}
* **Total Leaves**: {stats.total_leaves}
* **Avg Branching**: {stats.to_dict()['avg_branching']}
* **Avg Leaf Size**: {stats.to_dict()['avg_leaf_size']}

### 💡 Suggestions
* **Min Depth**: {tuned['min_depth']}
* **Min Hyponyms**: {tuned['min_hyponyms']}
* **Min Leaf Size**: {tuned['min_leaf_size']}
'''
        # Update history
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        entry = f"**{timestamp}**: {stats.total_nodes} nodes, {stats.total_leaves} leaves"
        history = [entry] + history if history else [entry]
        # Keep last 10 entries for state
        history = history[:10]

        # Hide stale warning (visible=False)
        return report, tuned['min_depth'], tuned['min_hyponyms'], tuned['min_leaf_size'], history, gr.update(visible=False)
        
    except Exception as e:
        logger.exception('Analysis failed')
        return f'Error: {str(e)}', 4, 50, 5, history, gr.update(visible=False)

def create_handler(topic, model, api_key, output_name):
    if not api_key:
        return None, 'Error: API Key required for LLM features. Set it in the Settings tab.'
    try:
        engine = LLMEngine(api_key=api_key, model=model)
        mgr = StructureManager()
        
        logger.info(f'GUI: Creating taxonomy for {topic}')
        yaml_str = engine.generate_dynamic_structure(topic)
        if not yaml_str:
            return None, 'Error: LLM failed to generate structure.'
            
        data = mgr.from_string(yaml_str)
        return save_and_preview(data, output_name)
    except Exception as e:
        logger.exception('Create failed')
        return None, f'Error: {str(e)}'

def categorize_handler(terms_text, model, api_key, output_name):
    if not api_key:
        return None, 'Error: API Key required. Set it in the Settings tab.'
    try:
        terms = [t.strip() for t in terms_text.split('\n') if t.strip()]
        if not terms:
            return None, 'Error: No terms provided.'
        
        engine = LLMEngine(api_key=api_key, model=model)
        mgr = StructureManager()
        
        # 1. Generate skeleton from samples
        logger.info(f'GUI: Categorizing {len(terms)} terms')
        sample = terms[:50]
        structure_yaml = engine.generate_structure(sample)
        if not structure_yaml:
            return None, 'Error: LLM failed to generate skeleton.'
        
        structure = mgr.from_string(structure_yaml)
        
        # 2. Categorize all terms
        categorized = engine.categorize_terms(terms, structure_yaml)
        if categorized:
            mgr.merge_categorized_data(structure, categorized)
            
        return save_and_preview(structure, output_name)
    except Exception as e:
        logger.exception('Categorize failed')
        return None, f'Error: {str(e)}'

def enrich_handler(input_yaml, topic, model, api_key, output_name):
    if not api_key:
        return None, 'Error: API Key required. Set it in the Settings tab.'
    try:
        engine = LLMEngine(api_key=api_key, model=model)
        mgr = StructureManager()
        
        if not input_yaml.strip():
            return None, 'Error: No YAML content provided.'
            
        logger.info(f'GUI: Enriching instructions for topic {topic}')
        enriched_yaml = engine.enrich_instructions(input_yaml, topic)
        if not enriched_yaml:
            return None, 'Error: Enrichment failed.'
            
        enriched = mgr.from_string(enriched_yaml)
        return save_and_preview(enriched, output_name)
    except Exception as e:
        logger.exception('Enrich failed')
        return None, f'Error: {str(e)}'

def lint_handler(file_obj, model, threshold, progress=gr.Progress()):
    if not file_obj:
        return 'Error: No file uploaded.', gr.update(visible=False), None
    
    progress(0, desc='Loading model... (this may take a moment)')
    try:
        from wildcards_gen.core.linter import lint_file, clean_structure
        
        output_path = file_obj.name
        # Run Lint - returns report and the original structure object
        result, structure = lint_file(output_path, model, float(threshold))
        issues = result.get('issues', [])
        
        if not issues:
            return '✅ **No outliers detected.** The structure looks semantically consistent!', gr.update(visible=False), None
            
        # Format Report
        total_outliers = sum(len(i['outliers']) for i in issues)
        report = f'### ⚠️ Found {total_outliers} Potential Outliers in {len(issues)} lists\n\n'
        report += '| Score | Item | Context (Path) |\n|---|---|---|\n'
        
        for issue in issues:
            path = issue['path']
            for out in issue['outliers']:
                score = out['score']
                term = out['term']
                report += f'| **{score:.2f}** | `{term}` | `{path}` |\n'
        
        # 3. Create cleaned version
        clean_data = clean_structure(structure, result)
        
        # Save to temp file for download
        from wildcards_gen.core.structure import StructureManager
        mgr = StructureManager()
        
        base_name = os.path.basename(output_path).replace('.yaml', '')
        clean_filename = f'{base_name}_cleaned.yaml'
        clean_path = os.path.join(os.path.dirname(output_path), clean_filename)
        
        # Use StructureManager to format the output
        with open(clean_path, 'w', encoding='utf-8') as f:
            f.write(mgr.to_string(clean_data))
            
        return report, gr.update(visible=True), clean_path
        
    except Exception as e:
        logger.exception('Linter failed')
        return f'Error: {str(e)}', gr.update(visible=False), None

# =============================================================================
# 6. UI CONSTRUCTION
# =============================================================================
def launch_gui(share=False):
    # Initial API key from config or env
    initial_key = config.api_key or os.environ.get('OPENROUTER_API_KEY', '')
    initial_hf_token = config.get('hf_token') or os.environ.get('HF_TOKEN', '')
    
    with gr.Blocks(title='Wildcards-Gen') as demo:
        # Header with API Key Status
        with gr.Row(elem_classes=['header-section']):
            with gr.Column(scale=4):
                gr.Markdown('# 🎴 Wildcards-Gen\n*Unified toolkit for hierarchical skeleton generation.*')
            with gr.Column(scale=1):
                api_status = gr.Markdown(
                    value=f"🔑 API: {'✅ Set' if initial_key else '❌ Not Set'}",
                    elem_id="api-status"
                )
        
        # Global State
        api_key_state = gr.State(initial_key)
        model_state = gr.State(config.model)
        
        # Global State
        api_key_state = gr.State(initial_key)
        model_state = gr.State(config.model)
        
        with gr.Tabs():
            # === TAB 1: CV DATASETS (Local) ===
            with gr.Tab('📸 CV Datasets'):
                # Header: Strategy & Source
                with gr.Row():
                     with gr.Column(scale=1):
                        ds_name = gr.Dropdown(
                            ['ImageNet', 'COCO', 'Open Images', 'Tencent ML-Images'], 
                            label='Source Dataset', 
                            value='ImageNet',
                            info='Choose source library.'
                        )
                     with gr.Column(scale=2):
                        ds_strategy = gr.Radio(
                            ['Standard', 'Smart'],
                            label='Extraction Mode',
                            value='Smart',
                            info='Smart Mode uses semantic analysis to prune meaningless intermediates.'
                        )
                        ds_info = gr.Markdown(
                            '_**ImageNet**: 21k classes. Best for general objects/animals._',
                            elem_id='ds-info'
                        )

                with gr.Row():
                    # --- Left Column: Configuration (Sidebar) ---
                    with gr.Column(scale=2, elem_classes=['dataset-config-panel']) as sidebar:
                        gr.Markdown('### 🛠️ Configuration', elem_classes=['section-header'])
                        
                        # ImageNet Specifics
                        with gr.Group(visible=True) as ds_imagenet_group:
                            with gr.Row():
                                ds_root = gr.Textbox(
                                    label='Root Synset', 
                                    value=config.get('datasets.imagenet.root_synset'),
                                    placeholder='entity.n.01',
                                    info='WordNet ID (e.g. entity.n.01).',
                                    scale=2
                                )
                                with gr.Column(scale=1):
                                    with gr.Accordion('🔍 WordNet Lookup', open=False):
                                        search_in = gr.Textbox(label='Search Term', placeholder='camera...', show_label=False)
                                        search_btn = gr.Button('Search', size='sm')
                                        search_out = gr.Markdown('')
                                        search_btn.click(search_wordnet, inputs=[search_in], outputs=[search_out])
                                        search_in.submit(search_wordnet, inputs=[search_in], outputs=[search_out])
                        
                        # General Depth
                        ds_depth = gr.Slider(1, 12, value=config.get('generation.default_depth'), step=1, label='Max Generation Depth')

                        # Smart Tuning
                        with gr.Group(visible=True) as smart_tuning_group:
                            gr.Markdown('**Smart Tuning**')
                            ds_smart_preset = gr.Radio(list(SMART_PRESETS.keys()), label='Preset', value='Balanced')
                            
                            with gr.Accordion('Fine-Tuning', open=False):
                                ds_min_depth = gr.Slider(0, 10, value=4, step=1, label='Significance Depth', info='Keep all categories shallower than this level regardless of descendant count (preserves top-level structure).')
                                ds_min_hyponyms = gr.Slider(0, 2000, value=50, step=10, label='Flattening Threshold', info='Merge category into a leaf list if it has fewer than X descendants total.')
                                ds_min_leaf = gr.Slider(1, 100, value=5, step=1, label='Min Leaf Size', info='If a resulting list has fewer than X items, merge them into the parent node.')
                                ds_merge_orphans = gr.Checkbox(label='Merge Orphans', value=True, info="Bubble up small lists into the parent's 'misc' key instead of keeping them as separate categories.")

                            with gr.Accordion('Semantic Cleaning', open=False):
                                ds_semantic_clean = gr.Checkbox(label="Enable Cleaning", value=False, info="Use embeddings to remove items that don't belong in their category (requires local model).")
                                ds_semantic_model = gr.Dropdown(['minilm', 'mpnet', 'qwen3'], value='minilm', label="Model")
                                ds_semantic_threshold = gr.Slider(0.01, 1.0, value=0.1, step=0.01, label="Threshold", info="Higher = more aggressive cleaning (removes more potential outliers).")
                                
                                gr.Markdown("---")
                                ds_semantic_arrangement = gr.Checkbox(label="Enable Arrangement", value=False, info="Automatically group flat lists into semantic sub-categories.")
                                
                                with gr.Row():
                                    ds_arrange_threshold = gr.Slider(label="Quality", minimum=0.0, maximum=1.0, value=0.1, step=0.05, info="Min probability required for a cluster.")
                                    ds_arrange_min_cluster = gr.Slider(label="Min Cluster", minimum=2, maximum=20, value=5, step=1, info="Minimum items required to form a new automated sub-category.")
                                
                                ds_arrange_method = gr.Dropdown(['eom', 'leaf'], value='eom', label="Cluster Method", info="'leaf' finds smaller, more specific groups; 'eom' finds stable clusters.")
                                ds_debug_arrangement = gr.Checkbox(label="Debug Logs", value=False)
                            
                            with gr.Accordion('Deep Tuning', open=False):
                                with gr.Row():
                                    ds_umap_neighbors = gr.Slider(2, 50, value=15, step=1, label="UMAP Neighbors", info="Balances local vs global structure. Lower values focus on very tight details.")
                                    ds_umap_dist = gr.Slider(0.0, 1.0, value=0.1, step=0.01, label="UMAP Min Dist", info="Determines how tight UMAP packs points. Lower = tighter clusters.")
                                with gr.Row():
                                    ds_arr_samples = gr.Slider(1, 20, value=5, step=1, label="Min Samples", info="HDBSCAN min samples. Higher = more points labeled as noise.")
                                    ds_orphans_template = gr.Textbox(label="Orphan Key", value="misc", placeholder="misc", info="Label for miscellaneous items (e.g., 'misc' or 'others').")
                                
                        # Filters
                        with gr.Accordion('Advanced Filters', open=False, visible=True) as adv_filter_group:
                            with gr.Row():
                                ds_filter = gr.Dropdown(['none', '1k', '21k'], label='Sub-Filter', value='none')
                                ds_strict = gr.Checkbox(label='Strict Lexical Match', value=True)
                            with gr.Row():
                                ds_blacklist = gr.Checkbox(label='Hide Abstract Concepts', value=False)
                                ds_bbox_only = gr.Checkbox(label='Legacy BBox Mode', value=False, visible=False) # Bound to ds_openimages_group logic but kept here
                            
                            ds_exclude_subtree = gr.Textbox(label='Exclude Subtrees', placeholder='comma-separated wnids')
                            ds_exclude_regex = gr.Textbox(label='Exclude Regex', placeholder='regex patterns')

                        with gr.Group(visible=False) as ds_openimages_group:
                            # This is a dummy group used for visibility logic in update_ds_ui
                            pass

                    # --- Right Column: Status & Preview ---
                    with gr.Column(scale=3):
                         with gr.Group(elem_classes=['status-panel']):
                             gr.Markdown('### 🚀 Status', elem_classes=['section-header'])
                             ds_summary = gr.Markdown('_Waiting for generation..._')

                         with gr.Group(elem_classes=['preview-panel']):
                             with gr.Row():
                                 with gr.Column(scale=4, min_width=0):
                                     gr.Markdown('**Preview output**')
                                 ds_out_name = gr.Textbox(label='Output Filename', value='skeleton.yaml', show_label=False, scale=2)
                             
                             ds_prev = gr.Code(language='yaml', label='YAML Preview', lines=35, max_lines=40, elem_classes=['preview-code'])

                         # Run Controls
                         with gr.Row():
                             ds_fast_preview = gr.Checkbox(label='⚡ Fast Preview', value=False, info='Limit to ~500 items.')
                             ds_btn = gr.Button('🚀 Generate Skeleton', variant='primary', size='lg')
                             ds_file = gr.File(label='Download Files', height=80, file_count='multiple')

            # === TAB 2: AI ASSISTANT (LLM) ===
            with gr.Tab('🧠 AI Assistant'):
                with gr.Tabs():
                    # Subtab: Create
                    with gr.Tab('✨ New Taxonomy'):
                        gr.Markdown('### Generate Taxonomy from Scratch')
                        with gr.Row():
                            with gr.Column():
                                cr_topic = gr.Textbox(label='Topic', placeholder='e.g. Types of Cyberpunk Augmentations')
                                cr_out = gr.Textbox(label='Output Filename', value='topic_skeleton.yaml')
                                cr_btn = gr.Button('✨ Generate', variant='primary')
                            with gr.Column():
                                cr_prev = gr.Code(language='yaml', label='Preview', lines=40, max_lines=40, elem_classes=['preview-code'])
                                cr_file = gr.File(label='Download')
                        cr_topic.change(update_cr_filename, inputs=[cr_topic], outputs=[cr_out])
                        cr_btn.click(create_handler, inputs=[cr_topic, model_state, api_key_state, cr_out], outputs=[cr_file, cr_prev])
                        cr_topic.submit(create_handler, inputs=[cr_topic, model_state, api_key_state, cr_out], outputs=[cr_file, cr_prev])

                    # Subtab: Categorize
                    with gr.Tab('🗂️ Categorize List'):
                        gr.Markdown('### Organize Flat List')
                        with gr.Row():
                            with gr.Column():
                                cat_terms = gr.TextArea(label='Raw Terms', placeholder='List of terms (one per line)...')
                                cat_out = gr.Textbox(label='Output Filename', value='categorized.yaml')
                                cat_btn = gr.Button('🗂️ Categorize', variant='primary')
                            with gr.Column():
                                cat_prev = gr.Code(language='yaml', label='Preview', lines=40, max_lines=40, elem_classes=['preview-code'])
                                cat_file = gr.File(label='Download')
                        cat_terms.change(update_cat_filename, inputs=[cat_terms], outputs=[cat_out])
                        cat_btn.click(categorize_handler, inputs=[cat_terms, model_state, api_key_state, cat_out], outputs=[cat_file, cat_prev])

                    # Subtab: Enrich
                    with gr.Tab('📝 Enrich (Context)'):
                        gr.Markdown('### Add Instructions')
                        with gr.Row():
                            with gr.Column():
                                en_yaml = gr.TextArea(label='Existing YAML', placeholder='Paste .yaml structure...')
                                en_topic = gr.Textbox(label='Context / Goal', value='AI image generation wildcards')
                                en_out = gr.Textbox(label='Output Filename', value='enriched.yaml')
                                en_btn = gr.Button('💡 Enrich', variant='primary')
                            with gr.Column():
                                en_prev = gr.Code(language='yaml', label='Preview', lines=40, max_lines=40, elem_classes=['preview-code'])
                                en_file = gr.File(label='Download')
                        en_topic.change(update_en_filename, inputs=[en_topic], outputs=[en_out])
                        en_btn.click(enrich_handler, inputs=[en_yaml, en_topic, model_state, api_key_state, en_out], outputs=[en_file, en_prev])
                        en_topic.submit(enrich_handler, inputs=[en_yaml, en_topic, model_state, api_key_state, en_out], outputs=[en_file, en_prev])

            # === TAB 3: QUALITY CONTROL ===
            with gr.Tab('🛡️ Quality Control'):
                gr.Markdown('### 🔬 Semantic Linter\n*Detect semantic outliers using embedding models.*')
                with gr.Row():
                    with gr.Column(scale=1):
                        lint_file = gr.File(label='Upload Skeleton YAML')
                        lint_model = gr.Dropdown(['qwen3', 'mpnet', 'minilm'], label='Model', value='qwen3')
                        lint_threshold = gr.Slider(0.01, 1.0, value=0.1, step=0.01, label='Sensitivity')
                        lint_btn = gr.Button('🕵️ Run Linter', variant='primary')
                    
                    with gr.Column(scale=2):
                        lint_output = gr.Markdown('Results will appear here...')
                        with gr.Group(visible=False) as lint_clean_group:
                            gr.Markdown('### ✨ Cleaned Skeleton')
                            lint_clean_file = gr.File(label='Download Cleaned YAML')
                
                lint_btn.click(lint_handler, inputs=[lint_file, lint_model, lint_threshold], outputs=[lint_output, lint_clean_group, lint_clean_file])

            # === TAB 4: SETTINGS ===
            with gr.Tab('⚙️ Settings'):
                with gr.Group():
                    gr.Markdown('**Keys**')
                    set_key = gr.Textbox(label='OpenRouter API Key', value=initial_key, type='password')
                    set_hf_token = gr.Textbox(label='Hugging Face Token', value=initial_hf_token, type='password', info="Required for gated models or to avoid rate limits.")
                    
                    set_save_keys = gr.Button('Update Keys')
                    
                    def update_keys(ak, hft):
                        if ak:
                            config.set('api_key', ak)
                            # Update config object for runtime
                            config._config['api_key'] = ak
                        
                        if hft:
                            os.environ['HF_TOKEN'] = hft
                            config.set('hf_token', hft)
                            
                        # Save to file
                        config.save()
                        
                        return ak, f"🔑 API: {'✅ Set' if ak else '❌ Not Set'} (Saved)"
                        
                    set_save_keys.click(update_keys, inputs=[set_key, set_hf_token], outputs=[api_key_state, api_status])
                    set_key.submit(update_keys, inputs=[set_key, set_hf_token], outputs=[api_key_state, api_status])
                    set_hf_token.submit(update_keys, inputs=[set_key, set_hf_token], outputs=[api_key_state, api_status])
                
                with gr.Group():
                    gr.Markdown('**Default LLM**')
                    set_model = gr.Dropdown([config.model, 'anthropic/claude-3.5-sonnet', 'google/gemini-pro'], label='Model', value=config.model, allow_custom_value=True)
                    set_save_model = gr.Button('Update Model')
                    set_save_model.click(lambda m: m, inputs=[set_model], outputs=[model_state])

        # === Event Wiring ===
        
        # Dataset Visibility
        ds_name.change(on_dataset_change, inputs=[ds_name, ds_strategy], outputs=[ds_imagenet_group, ds_strategy, smart_tuning_group, adv_filter_group, ds_openimages_group, ds_info])
        ds_strategy.change(on_dataset_change, inputs=[ds_name, ds_strategy], outputs=[ds_imagenet_group, ds_strategy, smart_tuning_group, adv_filter_group, ds_openimages_group, ds_info])

        # Filename Updates
        config_inputs = [ds_name, ds_root, ds_depth, ds_strategy, ds_min_depth, ds_min_hyponyms, ds_min_leaf, ds_bbox_only]
        for comp in config_inputs:
            comp.change(update_ds_filename, inputs=config_inputs, outputs=[ds_out_name])
        
        # Dataset Generation components
        all_gen_inputs = [
            ds_name, ds_strategy, ds_root, ds_depth, ds_out_name,
            gr.State(True), ds_filter, ds_strict, ds_blacklist, # with_glosses=True default
            ds_min_depth, ds_min_hyponyms, ds_min_leaf, ds_merge_orphans,
            ds_bbox_only,
            ds_semantic_clean, ds_semantic_model, ds_semantic_threshold,
            ds_semantic_arrangement, ds_arrange_threshold, ds_arrange_min_cluster,
            ds_exclude_subtree, ds_exclude_regex,
            ds_arrange_method, ds_debug_arrangement,
            ds_umap_neighbors, ds_umap_dist, ds_arr_samples, ds_orphans_template,
            ds_fast_preview
        ]
        
        # --- Live Preview (Instant Feedback) ---
        # When Fast Preview is ON, sliding should trigger generation with debounce
        live_preview_triggers = [
            ds_depth.change, ds_min_depth.change, ds_min_hyponyms.change, ds_min_leaf.change,
            ds_semantic_threshold.change, ds_arrange_threshold.change, ds_arrange_min_cluster.change,
            ds_merge_orphans.change, ds_semantic_clean.change, ds_semantic_arrangement.change,
            ds_umap_neighbors.change, ds_umap_dist.change, ds_arr_samples.change
        ]
        
        # Wire each trigger to the live_preview_handler
        # Note: Gradio 6.x uses 'always_last' as the default for .change() events
        for trigger in live_preview_triggers:
            trigger(
                live_preview_handler,
                inputs=all_gen_inputs,
                outputs=[ds_prev, ds_summary, ds_file],
                concurrency_limit=1,
                show_progress="hidden"
            )
        
        # Smart Presets
        def apply_smart_preset(p, dataset_name):
            if dataset_name in DATASET_PRESET_OVERRIDES and p in DATASET_PRESET_OVERRIDES[dataset_name]:
                return DATASET_PRESET_OVERRIDES[dataset_name][p]
            return SMART_PRESETS.get(p, [gr.update()]*7)

        # Smart Presets
        def apply_smart_preset(p, dataset_name):
            if dataset_name in DATASET_PRESET_OVERRIDES and p in DATASET_PRESET_OVERRIDES[dataset_name]:
                return DATASET_PRESET_OVERRIDES[dataset_name][p]
            return SMART_PRESETS.get(p, [gr.update()]*7)
            
        ds_smart_preset.change(apply_smart_preset, inputs=[ds_smart_preset, ds_name], outputs=[ds_min_depth, ds_min_hyponyms, ds_min_leaf, ds_merge_orphans, ds_semantic_clean, ds_semantic_arrangement, ds_arrange_method])

        
        ds_btn.click(generate_dataset_handler, inputs=all_gen_inputs, outputs=[ds_prev, ds_summary, ds_file])



    # Configure logging to reduce spam
    logging.getLogger("transformers").setLevel(logging.ERROR)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
    logging.getLogger("huggingface_hub").setLevel(logging.WARNING)

    server_name = config.get('gui.server_name')
    server_port = config.get('gui.server_port')
    
    # HF Token Handling
    hf_token = config.get('hf_token') or os.environ.get('HF_TOKEN')
    if hf_token:
        os.environ['HF_TOKEN'] = hf_token
    
    logger.info(f'🌐 GUI is starting at http://{server_name or "127.0.0.1"}:{server_port or 7860}')
    
    # NOTE: Gradio 6.0 migration: theme and css moved to launch()
    demo.launch(
        share=share, 
        server_name=server_name, 
        server_port=server_port, 
        theme=gr.themes.Soft(),
        css=CUSTOM_CSS
    )
