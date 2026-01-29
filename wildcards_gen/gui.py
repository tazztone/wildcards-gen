import gradio as gr
import os
import yaml
import logging
from nltk.corpus import wordnet as wn
from wildcards_gen.core.datasets import imagenet, coco, openimages, tencent
from wildcards_gen.core.structure import StructureManager
from wildcards_gen.core.config import config
from wildcards_gen.core.llm import LLMEngine

logger = logging.getLogger(__name__)

from .core.presets import SMART_PRESETS, DATASET_PRESET_OVERRIDES

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
        
    return output_path, yaml_str

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
    
    # Returns: visibility_updates (5) + info_update (1) + reset_analysis (2)
    return visibility_updates + [
        gr.update(value=info_text),
        gr.update(value=''),      # ds_analysis_output
        gr.update(visible=False)  # apply_output_row
    ]


def generate_dataset_handler(
    dataset_name, strategy, root, depth, output_name,
    with_glosses, filter_set, strict_filter, blacklist_abstract,
    min_depth, min_hyponyms, min_leaf, merge_orphans,
    bbox_only,
    exclude_subtree=None, exclude_regex=None,
    progress=gr.Progress()
):
    progress(0, desc='Initializing...')
    try:
        is_smart = (strategy == 'Smart')
        if dataset_name == 'ImageNet':
            if not root:
                return None, 'Error: Root synset required for ImageNet (e.g. entity.n.01)'
            progress(0.2, desc='Downloading ImageNet metadata...')
            data = imagenet.generate_imagenet_tree(
                root,
                max_depth=int(depth),
                filter_set=filter_set if filter_set != 'none' else None,
                with_glosses=with_glosses,
                strict_filter=strict_filter,
                blacklist_abstract=blacklist_abstract,
                smart=is_smart,
                min_significance_depth=int(min_depth),
                min_hyponyms=int(min_hyponyms),
                min_leaf_size=int(min_leaf),
                merge_orphans=merge_orphans,
                exclude_regex=exclude_regex,
                exclude_subtree=exclude_subtree
            )
        elif dataset_name == 'COCO':
            progress(0.2, desc='Loading COCO API...')
            data = coco.generate_coco_hierarchy(
                with_glosses=with_glosses
            )
        elif dataset_name == 'Open Images':
            progress(0.2, desc='Loading Open Images metadata...')
            data = openimages.generate_openimages_hierarchy(
                max_depth=int(depth),
                with_glosses=with_glosses,
                smart=is_smart,
                min_significance_depth=int(min_depth),
                min_hyponyms=int(min_hyponyms),
                min_leaf_size=int(min_leaf),
                merge_orphans=merge_orphans,
                bbox_only=bbox_only
            )
        elif dataset_name == 'Tencent ML-Images':
            progress(0.2, desc='Loading Tencent dictionary...')
            data = tencent.generate_tencent_hierarchy(
                max_depth=int(depth),
                with_glosses=with_glosses,
                smart=is_smart,
                min_significance_depth=int(min_depth),
                min_hyponyms=int(min_hyponyms),
                min_leaf_size=int(min_leaf),
                merge_orphans=merge_orphans
            )
        else:
            return None, f'Unknown dataset: {dataset_name}'
            
        return save_and_preview(data, output_name)
    except Exception as e:
        logger.exception('Dataset generation failed')
        return None, f'Error: {str(e)}'

def analyze_handler(
    dataset_name, root, depth, filter_set, strict_filter, blacklist_abstract, bbox_only,
    progress=gr.Progress()
):
    """Run dry-run analysis and return report + suggestions."""
    progress(0, desc='Analyzing structure...')
    try:
        data = None
        if dataset_name == 'ImageNet':
            if not root: return 'Error: Root required', 4, 50, 5
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
            return 'Analysis not supported for this dataset.', 4, 50, 5
            
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
        return report, tuned['min_depth'], tuned['min_hyponyms'], tuned['min_leaf_size']
        
    except Exception as e:
        logger.exception('Analysis failed')
        return f'Error: {str(e)}', 4, 50, 5

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

def launch_gui(share=False):
    # Initial API key from config or env
    initial_key = config.api_key or os.environ.get('OPENROUTER_API_KEY', '')
    
    with gr.Blocks(title='Wildcards-Gen') as demo:
        # Header with API Key Status
        with gr.Row():
            gr.Markdown('# 🎴 Wildcards-Gen')
            api_status = gr.Markdown(
                value=f"🔑 API: {'✅ Set' if initial_key else '❌ Not Set'}",
                elem_id="api-status"
            )
        gr.Markdown('*Unified toolkit for hierarchical skeleton generation.*')
        
        # Global State
        api_key_state = gr.State(initial_key)
        model_state = gr.State(config.model)
        
        with gr.Tabs():
            # === TAB 1: BUILDER (Consolidated) ===
            with gr.Tab('🏗️ Builder'):
                
                # Source Selection
                with gr.Row():
                    source_type = gr.Radio(
                        ['Dataset (CV)', 'New Topic (LLM)', 'Raw List (LLM)'],
                        label='Source Type',
                        value='Dataset (CV)',
                        info='Choose how you want to generate the hierarchy.'
                    )
                
                # --- Group: Dataset (CV) ---
                with gr.Group(visible=True) as grp_dataset:
                    gr.Markdown('### Generate from CV Datasets — *100% Local & Free*')
                    
                    # WordNet Search
                    with gr.Accordion('🔍 WordNet ID Lookup', open=False):
                        gr.Markdown('### 🔍 Dictionary Lookup\n*Find the specific WordNet synset ID required for ImageNet root settings.*')
                        with gr.Row():
                            search_in = gr.Textbox(label='Search Term', placeholder='e.g. camera, dog, sword', scale=3, info='Lookup meanings and synset IDs (e.g. \'camera\' -> \'camera.n.01\').')
                            search_btn = gr.Button('Search', scale=1)
                        search_out = gr.Markdown('Results appear here...')
                        search_btn.click(search_wordnet, inputs=[search_in], outputs=[search_out])
                    
                    with gr.Row():
                        # Left Column: Configuration
                        with gr.Column(scale=1):
                            with gr.Group():
                                gr.Markdown('**Dataset & Strategy**')
                                ds_name = gr.Dropdown(
                                    ['ImageNet', 'COCO', 'Open Images', 'Tencent ML-Images'], 
                                    label='Source', 
                                    value='ImageNet',
                                    info='Source dataset for hierarchy generation.'
                                )
                                ds_info = gr.Markdown(
                                    '_**ImageNet**: 21k classes. Best for general objects/animals._',
                                    elem_id='ds-info'
                                )
                                ds_strategy = gr.Radio(
                                    ['Standard', 'Smart'],
                                    label='Extraction Mode',
                                    value='Smart',
                                    info='Smart: Uses semantic analysis to prune meaningless intermediates and flatten deep lists.'
                                )
                            
                            with gr.Group(visible=True) as ds_imagenet_group:
                                gr.Markdown('**ImageNet Configuration**')
                                ds_root = gr.Textbox(
                                    label='Root Synset', 
                                    value=config.get('datasets.imagenet.root_synset'),
                                    placeholder='entity.n.01',
                                    info='WordNet ID (e.g. entity.n.01). Use Lookup above to find others.'
                                )
                                ds_presets = gr.Dropdown(
                                    choices=list(COMMON_ROOTS.keys()),
                                    label='Quick Presets',
                                    info='Select common ImageNet high-level categories.'
                                )
                                def apply_preset(p):
                                    val = COMMON_ROOTS.get(p, '')
                                    return val if val else gr.update()
                                ds_presets.change(apply_preset, inputs=[ds_presets], outputs=[ds_root])
                            
                            with gr.Group():
                                gr.Markdown('**Hierarchy Depth**')
                                ds_depth = gr.Slider(1, 12, value=config.get('generation.default_depth'), step=1, label='Max Generation Depth', info='Maximum recursion limit for the hierarchy tree.')
                            
                            with gr.Accordion('Smart Tuning Parameters', open=True, visible=True) as smart_tuning_group:
                                gr.Markdown('_Smart Mode uses WordNet to analyze semantic importance. Adjust these to control granularity._')
                                
                                ds_smart_preset = gr.Radio(list(SMART_PRESETS.keys()), label='Preset', value='Balanced', info='Semantic pruning levels from Ultra-Detailed to Ultra-Flat.')
                                ds_min_depth = gr.Slider(0, 10, value=4, step=1, label='Significance Depth', info='Force categories if shallower than this.')
                                ds_min_hyponyms = gr.Slider(0, 2000, value=50, step=10, label='Flattening Threshold', info='Keep as category if more descendants than this.')
                                ds_min_leaf = gr.Slider(1, 100, value=5, step=1, label='Min Leaf Size', info='Merge small lists into parent.')
                                ds_merge_orphans = gr.Checkbox(label='Merge Orphans', value=True, info='Group small pruned lists into a \'misc\' key.')
                                
                                def apply_smart_preset(p, dataset_name):
                                    # Check dataset-specific overrides first
                                    if dataset_name in DATASET_PRESET_OVERRIDES:
                                        overrides = DATASET_PRESET_OVERRIDES[dataset_name]
                                        if p in overrides:
                                            return overrides[p]
                                    # Fall back to universal presets
                                    if p in SMART_PRESETS:
                                        return SMART_PRESETS[p]
                                    return [gr.update()]*4                            
                                ds_smart_preset.change(apply_smart_preset, inputs=[ds_smart_preset, ds_name], outputs=[ds_min_depth, ds_min_hyponyms, ds_min_leaf, ds_merge_orphans])

                                # === NEW: Analysis Tools ===
                                gr.Markdown('### 📊 Dataset Analysis\n*Examine the raw hierarchy to find the best \'Smart\' flattening thresholds for this specific dataset and root.*')
                                with gr.Row():
                                    ds_analyze_btn = gr.Button('🔍 Analyze Structure', size='sm')
                                ds_analysis_output = gr.Markdown('')
                                with gr.Row(visible=False) as apply_output_row:
                                    gr.Markdown('💡 **Optimization**: Apply the suggested thresholds found during analysis.')
                                    ds_apply_suggest = gr.Button('✅ Apply Suggestions', size='sm', variant='secondary')
                                    # Hidden states to store suggestion values
                                    sug_d = gr.State(4)
                                    sug_h = gr.State(50)
                                    sug_l = gr.State(5)
                                
                                ds_apply_suggest.click(
                                    lambda d, h, l: (d, h, l),
                                    inputs=[sug_d, sug_h, sug_l],
                                    outputs=[ds_min_depth, ds_min_hyponyms, ds_min_leaf]
                                )
                            
                            with gr.Accordion('Advanced Filtering (ImageNet)', open=False, visible=True) as adv_filter_group:
                                ds_filter = gr.Dropdown(['none', '1k', '21k'], label='Sub-Filter', value='none', info='ImageNet subsets (1k/21k classes).')
                                ds_strict = gr.Checkbox(label='Strict Lexical Match', value=True, info='Prevent ambiguous semantic paths.')
                                ds_blacklist = gr.Checkbox(label='Hide Abstract Concepts', value=False, info='Hide non-visual WordNet concepts.')
                                # === NEW: Exclusion Filters ===
                                with gr.Row():
                                    ds_exclude_subtree = gr.Textbox(label='Exclude Subtrees', placeholder='e.g. dog.n.01, vehicle.n.01 (Comma separated)', info='Remove entire branches (e.g., \'clothing.n.01\').', scale=3)
                                    ds_exclude_presets = gr.Dropdown(
                                        choices=list(COMMON_ROOTS.keys()),
                                        label='Quick Exclude',
                                        info='Select category to add to exclusion list.',
                                        scale=1
                                    )
                                    
                                    def append_exclusion(current_val, new_key):
                                        wnid = COMMON_ROOTS.get(new_key, '')
                                        if not wnid: return current_val
                                        if not current_val: return wnid
                                        if wnid in current_val: return current_val # Avoid dupes
                                        return f'{current_val}, {wnid}'
                                        
                                    ds_exclude_presets.change(append_exclusion, inputs=[ds_exclude_subtree, ds_exclude_presets], outputs=[ds_exclude_subtree])
                                    
                                ds_exclude_regex = gr.Textbox(label='Exclude Regex', placeholder='e.g. .*sex.*, ^bad_prefix (Comma separated)', info='Skip names matching regex.')
                            
                            with gr.Group(visible=False) as ds_openimages_group:
                                ds_bbox_only = gr.Checkbox(label='Legacy BBox Mode (600 classes)', value=False, info='Limit to ~600 primary detection classes.')
                            
                            with gr.Row():
                                ds_glosses = gr.Checkbox(label='Include Instructions', value=True, info='Add WordNet definitions as instructions.')
                                ds_out = gr.Textbox(label='Output Filename', info='Auto-generated based on configuration.', value=update_ds_filename('ImageNet', config.get('datasets.imagenet.root_synset'), config.get('generation.default_depth'), 'Smart', 4, 50, 5, False))
                            
                            gr.Markdown('### 🚀 Build Skeleton\n*Generate the WordNet-linked hierarchy based on your source and pruning settings.*')
                            ds_btn = gr.Button('🚀 Generate Skeleton', variant='primary', size='lg')

                        # Right Column: Preview
                        with gr.Column(scale=1):
                            ds_file = gr.File(label='Download YAML')
                            ds_prev = gr.Code(language='yaml', label='Preview', lines=25)

                # --- Group: Create (Topic) ---
                with gr.Group(visible=False) as grp_create:
                    gr.Markdown('### Generate Taxonomy from Scratch — *LLM Powered*')
                    with gr.Row():
                        with gr.Column():
                            cr_topic = gr.Textbox(label='Topic', placeholder='e.g. Types of Cyberpunk Augmentations', info='Phrase describing the taxonomy for AI to brainstorm.')
                            cr_out = gr.Textbox(label='Output Filename', value='topic_skeleton.yaml', info='Filename for the generated YAML skeleton.')
                            cr_topic.change(update_cr_filename, inputs=[cr_topic], outputs=[cr_out])
                            gr.Markdown('*Click to brainstorm a complete hierarchy for this topic via AI.*')
                            cr_btn = gr.Button('✨ Generate', variant='primary')
                        with gr.Column():
                            cr_file = gr.File(label='Download YAML')
                            cr_prev = gr.Code(language='yaml', label='Preview', lines=20)
                    cr_btn.click(create_handler, inputs=[cr_topic, model_state, api_key_state, cr_out], outputs=[cr_file, cr_prev])

                # --- Group: Categorize (List) ---
                with gr.Group(visible=False) as grp_categorize:
                    gr.Markdown('### Organize Flat List into Hierarchy — *LLM Powered*')
                    with gr.Row():
                        with gr.Column():
                            cat_terms = gr.TextArea(label='Raw Terms', placeholder='Lion\nTiger\nLeopard\n...', info='List of terms (one per line) for AI to organize.')
                            cat_out = gr.Textbox(label='Output Filename', value='categorized.yaml', info='Filename for the organized output.')
                            cat_terms.change(update_cat_filename, inputs=[cat_terms], outputs=[cat_out])
                            gr.Markdown('*Organize your terms into a logical structure with categories and sub-categories.*')
                            cat_btn = gr.Button('🗂️ Categorize', variant='primary')
                        with gr.Column():
                            cat_file = gr.File(label='Download YAML')
                            cat_prev = gr.Code(language='yaml', label='Preview', lines=20)
                    cat_btn.click(categorize_handler, inputs=[cat_terms, model_state, api_key_state, cat_out], outputs=[cat_file, cat_prev])

                # Source Toggle Logic
                def on_source_change(choice):
                    return [
                        gr.update(visible=(choice == 'Dataset (CV)')),
                        gr.update(visible=(choice == 'New Topic (LLM)')),
                        gr.update(visible=(choice == 'Raw List (LLM)'))
                    ]
                source_type.change(on_source_change, inputs=[source_type], outputs=[grp_dataset, grp_create, grp_categorize])

            # === TAB 2: TOOLS (Consolidated) ===
            with gr.Tab('🛠️ Tools'):
                with gr.Tabs():
                    # --- Subtab: Enrich ---
                    with gr.Tab('✨ Enrich'):
                        gr.Markdown('### Add Instructions to Existing YAML — *LLM Powered*')
                        with gr.Row():
                            with gr.Column():
                                en_yaml = gr.TextArea(label='Existing YAML', placeholder='Paste your .yaml structure here...', info='Input YAML for adding \'# instruction:\' comments.')
                                en_topic = gr.Textbox(label='Context / Goal', value='AI image generation wildcards', info='Guides AI instructions (e.g. \'Stable Diffusion\').')
                                en_out = gr.Textbox(label='Output Filename', value='enriched.yaml', info='Filename for the enriched output.')
                                en_topic.change(update_en_filename, inputs=[en_topic], outputs=[en_out])
                                gr.Markdown('*Add instruction comments to your existing YAML based on the context/goal.*')
                                en_btn = gr.Button('💡 Enrich', variant='primary')
                            with gr.Column():
                                en_file = gr.File(label='Download YAML')
                                en_prev = gr.Code(language='yaml', label='Preview', lines=20)
                        en_btn.click(enrich_handler, inputs=[en_yaml, en_topic, model_state, api_key_state, en_out], outputs=[en_file, en_prev])

                    # --- Subtab: Linter ---
                    with gr.Tab('🔬 Semantic Linter'):
                        gr.Markdown('### Detect Semantic Outliers using Embeddings — *Local ML*')
                        with gr.Row():
                            with gr.Column(scale=1):
                                lint_file = gr.File(label='Upload Skeleton YAML (Select the YAML skeleton to analyze.)', file_types=['.yaml'])
                                lint_model = gr.Dropdown(
                                    ['qwen3', 'mpnet', 'minilm'], 
                                    label='Embedding Model', 
                                    value='qwen3',
                                    info='Qwen3 (Best), MPNet (Fast), MiniLM (Fastest)'
                                )
                                lint_threshold = gr.Slider(0.01, 1.0, value=0.1, step=0.01, label='Sensitivity Threshold', info='Higher = stricter outlier detection.')
                                gr.Markdown('*Analyze local embeddings to identify nodes that are semantically distinct from their parents.*')
                                lint_btn = gr.Button('🕵️ Run Linter', variant='primary')
                            
                            with gr.Column(scale=2):
                                lint_output = gr.Markdown('Results will appear here...')
                                with gr.Group(visible=False) as lint_clean_group:
                                    gr.Markdown('### ✨ Cleaned Skeleton\n*Outliers have been automatically removed. Download the refined structure below:*')
                                    lint_clean_file = gr.File(label='Download Cleaned YAML')
                        
                        lint_btn.click(lint_handler, inputs=[lint_file, lint_model, lint_threshold], outputs=[lint_output, lint_clean_group, lint_clean_file])

            # === TAB 3: SETTINGS ===
            with gr.Tab('⚙️ Settings'):
                gr.Markdown('### Configuration')
                with gr.Group():
                    gr.Markdown('**API Key** — *Required for LLM tabs (Create, Categorize, Enrich)*')
                    set_key = gr.Textbox(label='OpenRouter API Key', value=initial_key, type='password', info='Required for LLM features (Session-only).')
                    set_save_key = gr.Button('Update API Key')
                    
                    def update_api_key(new_key):
                        status = f"🔑 API: {'✅ Set' if new_key else '❌ Not Set'}"
                        return new_key, status
                    
                    set_save_key.click(update_api_key, inputs=[set_key], outputs=[api_key_state, api_status])
                
                with gr.Group():
                    gr.Markdown('**Default LLM Model**')
                    set_model = gr.Dropdown(
                        [config.model, 'anthropic/claude-3.5-sonnet', 'openai/gpt-4o', 'google/gemini-pro'],
                        label='Model', 
                        value=config.model, 
                        allow_custom_value=True,
                        info='The LLM to use for generation/categorization.'
                    )
                    set_save_model = gr.Button('Update Model')
                    set_save_model.click(lambda m: m, inputs=[set_model], outputs=[model_state])
                
                gr.Markdown('> *Settings are for this session only. Edit `wildcards-gen.yaml` for persistence.*')

        # Wire up dataset listeners again (copied from original, logic remains same)
        # Indented to be inside gr.Blocks
        ds_name.change(
            on_dataset_change, 
            inputs=[ds_name, ds_strategy], 
            outputs=[ds_imagenet_group, ds_strategy, smart_tuning_group, adv_filter_group, ds_openimages_group, ds_info, ds_analysis_output, apply_output_row]
        )
        
        ds_strategy.change(
            on_dataset_change, 
            inputs=[ds_name, ds_strategy], 
            outputs=[ds_imagenet_group, ds_strategy, smart_tuning_group, adv_filter_group, ds_openimages_group, ds_info, ds_analysis_output, apply_output_row]
        )
        
        for comp in [ds_name, ds_root, ds_depth, ds_strategy, ds_min_depth, ds_min_hyponyms, ds_min_leaf, ds_bbox_only]:
            comp.change(update_ds_filename, inputs=[ds_name, ds_root, ds_depth, ds_strategy, ds_min_depth, ds_min_hyponyms, ds_min_leaf, ds_bbox_only], outputs=[ds_out])
        
        # Helper to parse text inputs into lists
        def parse_csv(text):
            if not text: return None
            return [t.strip() for t in text.split(',') if t.strip()]

        ds_analyze_btn.click(
            analyze_handler,
            inputs=[ds_name, ds_root, ds_depth, ds_filter, ds_strict, ds_blacklist, ds_bbox_only],
            outputs=[ds_analysis_output, sug_d, sug_h, sug_l]
        ).then(lambda r: gr.update(visible=True if 'Error' not in r else False), inputs=[ds_analysis_output], outputs=[apply_output_row])

        ds_btn.click(
            lambda *args: generate_dataset_handler(
                *args[:-2], 
                exclude_subtree=parse_csv(args[-2]), 
                exclude_regex=parse_csv(args[-1])
            ),
            inputs=[
                ds_name, ds_strategy, ds_root, ds_depth, ds_out, 
                ds_glosses, ds_filter, ds_strict, ds_blacklist, 
                ds_min_depth, ds_min_hyponyms, ds_min_leaf, ds_merge_orphans, 
                ds_bbox_only,
                ds_exclude_subtree, ds_exclude_regex
            ],
            outputs=[ds_file, ds_prev]
        )

    server_name = config.get('gui.server_name')
    server_port = config.get('gui.server_port')
    logger.info(f'🌐 GUI is starting at http://{server_name or '127.0.0.1'}:{server_port or 7860}')
    demo.launch(share=share, server_name=server_name, server_port=server_port, theme=gr.themes.Soft())