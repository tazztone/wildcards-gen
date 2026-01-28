
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

def save_and_preview(data, output_name):
    """Helper to save structure and return path + content."""
    mgr = StructureManager()
    yaml_str = mgr.to_string(data)
    
    output_dir = config.output_dir
    os.makedirs(output_dir, exist_ok=True)
    if not output_name.endswith(".yaml"):
        output_name += ".yaml"
    output_path = os.path.join(output_dir, output_name)
    
    with open(output_path, "w", encoding='utf-8') as f:
        f.write(yaml_str)
        
    return output_path, yaml_str

def search_wordnet(query):
    """Search for synsets matching the query."""
    if not query or len(query) < 2:
        return "Please enter at least 2 characters."
    
    try:
        synsets = wn.synsets(query.replace(' ', '_'))
        if not synsets:
            return f"No results found for '{query}'."
        
        results = []
        for s in synsets:
            wnid = f"{s.pos()}{s.offset():08d}"
            results.append(f"**{s.name()}** (`{wnid}`)\n_{s.definition()}_\n")
            
        return "\n".join(results)
    except Exception as e:
        return f"Error: {str(e)}"

def clean_filename(s):
    """Clean string for use in filename."""
    import re
    s = s.lower().replace(" ", "_")
    return re.sub(r'[^a-z0-9_.]', '', s)

def update_ds_filename(name, root, depth, strategy, bbox_only=False):
    root_part = clean_filename(root.split('.')[0]) if '.' in root else clean_filename(root)
    name_part = clean_filename(name)
    strategy_suffix = "_smart" if strategy == "Smart" else ""
    bbox_suffix = "_bbox" if (bbox_only and name == "Open Images") else ""
    return f"{name_part}_{root_part}_d{depth}{strategy_suffix}{bbox_suffix}.yaml" if root_part else f"{name_part}_d{depth}{strategy_suffix}{bbox_suffix}.yaml"

def update_cr_filename(topic):
    if not topic: return "topic_skeleton.yaml"
    return f"{clean_filename(topic)[:30]}_skeleton.yaml"

def update_cat_filename(terms):
    if not terms: return "categorized.yaml"
    first_term = terms.split('\n')[0][:20]
    return f"categorized_{clean_filename(first_term)}.yaml"

def update_en_filename(topic):
    if not topic: return "enriched.yaml"
    return f"enriched_{clean_filename(topic)[:20]}.yaml"

def update_dataset_inputs(dataset_name, strategy):
    """Update visibility of inputs based on dataset and strategy selections."""
    is_imagenet = (dataset_name == "ImageNet")
    can_use_smart = dataset_name in ["ImageNet", "Open Images", "Tencent ML-Images"]
    is_smart = (strategy == "Smart") and can_use_smart

    return [
        gr.update(visible=is_imagenet),                         # ds_root
        gr.update(visible=is_imagenet),                         # ds_presets
        gr.update(interactive=can_use_smart, value="Smart" if (can_use_smart and dataset_name != "ImageNet") else strategy), # ds_strategy
        gr.update(visible=not is_smart),                        # ds_depth_row (only for Standard)
        gr.update(visible=is_smart),                            # smart_preset_row
        gr.update(visible=is_smart),                            # smart_tuning_row
        gr.update(visible=is_imagenet),                         # ds_filter
        gr.update(visible=is_imagenet),                         # ds_strict
        gr.update(visible=is_imagenet),                         # ds_blacklist
    ]

def generate_dataset_handler(
    dataset_name, strategy, root, depth, output_name,
    with_glosses, filter_set, strict_filter, blacklist_abstract,
    min_depth, min_hyponyms, min_leaf, merge_orphans,
    bbox_only,
    progress=gr.Progress()
):
    progress(0, desc="Initializing...")
    try:
        is_smart = (strategy == "Smart")
        if dataset_name == "ImageNet":
            if not root:
                return None, "Error: Root synset required for ImageNet (e.g. animal.n.01)"
            progress(0.2, desc="Downloading ImageNet metadata...")
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
                merge_orphans=merge_orphans
            )
        elif dataset_name == "COCO":
            progress(0.2, desc="Loading COCO API...")
            data = coco.generate_coco_hierarchy(
                with_glosses=with_glosses
            )
        elif dataset_name == "Open Images":
            progress(0.2, desc="Loading Open Images metadata...")
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
        elif dataset_name == "Tencent ML-Images":
            progress(0.2, desc="Loading Tencent dictionary...")
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
            return None, f"Unknown dataset: {dataset_name}"
            
        return save_and_preview(data, output_name)
    except Exception as e:
        logger.exception("Dataset generation failed")
        return None, f"Error: {str(e)}"

def create_handler(topic, model, api_key, output_name):
    if not api_key:
        return None, "Error: API Key required for LLM features. Set it in the Settings tab."
    try:
        engine = LLMEngine(api_key=api_key, model=model)
        mgr = StructureManager()
        
        logger.info(f"GUI: Creating taxonomy for {topic}")
        yaml_str = engine.generate_dynamic_structure(topic)
        if not yaml_str:
            return None, "Error: LLM failed to generate structure."
            
        data = mgr.from_string(yaml_str)
        return save_and_preview(data, output_name)
    except Exception as e:
        logger.exception("Create failed")
        return None, f"Error: {str(e)}"

def categorize_handler(terms_text, model, api_key, output_name):
    if not api_key:
        return None, "Error: API Key required. Set it in the Settings tab."
    try:
        terms = [t.strip() for t in terms_text.split("\n") if t.strip()]
        if not terms:
            return None, "Error: No terms provided."
        
        engine = LLMEngine(api_key=api_key, model=model)
        mgr = StructureManager()
        
        # 1. Generate skeleton from samples
        logger.info(f"GUI: Categorizing {len(terms)} terms")
        sample = terms[:50]
        structure_yaml = engine.generate_structure(sample)
        if not structure_yaml:
            return None, "Error: LLM failed to generate skeleton."
        
        structure = mgr.from_string(structure_yaml)
        
        # 2. Categorize all terms
        categorized = engine.categorize_terms(terms, structure_yaml)
        if categorized:
            mgr.merge_categorized_data(structure, categorized)
            
        return save_and_preview(structure, output_name)
    except Exception as e:
        logger.exception("Categorize failed")
        return None, f"Error: {str(e)}"

def enrich_handler(input_yaml, topic, model, api_key, output_name):
    if not api_key:
        return None, "Error: API Key required. Set it in the Settings tab."
    try:
        engine = LLMEngine(api_key=api_key, model=model)
        mgr = StructureManager()
        
        if not input_yaml.strip():
            return None, "Error: No YAML content provided."
            
        logger.info(f"GUI: Enriching instructions for topic {topic}")
        enriched_yaml = engine.enrich_instructions(input_yaml, topic)
        if not enriched_yaml:
            return None, "Error: Enrichment failed."
            
        enriched = mgr.from_string(enriched_yaml)
        return save_and_preview(enriched, output_name)
    except Exception as e:
        logger.exception("Enrich failed")
        return None, f"Error: {str(e)}"

def launch_gui(share=False):
    # Initial API key from config or env
    initial_key = config.api_key or os.environ.get("OPENROUTER_API_KEY", "")
    
    with gr.Blocks(title="Wildcards-Gen", theme=gr.themes.Soft()) as demo:
        # Header with API Key Status
        with gr.Row():
            gr.Markdown("# 🎴 Wildcards-Gen")
            api_status = gr.Markdown(
                value=f"🔑 API: {'✅ Set' if initial_key else '❌ Not Set'}",
                elem_id="api-status"
            )
        gr.Markdown("*Unified toolkit for hierarchical skeleton generation.*")
        
        # Global State
        api_key_state = gr.State(initial_key)
        model_state = gr.State(config.model)
        
        with gr.Tabs():
            # === TAB 1: DATASETS (Local & Free) ===
            with gr.Tab("🗂️ Datasets"):
                gr.Markdown("### Generate from CV Datasets — *100% Local & Free*")
                
                # WordNet Search (Moved to top for discoverability)
                with gr.Accordion("🔍 WordNet ID Lookup", open=False):
                    gr.Markdown("*Find the right synset ID for ImageNet roots.*")
                    with gr.Row():
                        search_in = gr.Textbox(label="Search Term", placeholder="e.g. camera, dog, sword", scale=3)
                        search_btn = gr.Button("Search", scale=1)
                    search_out = gr.Markdown("Results appear here...")
                    search_btn.click(search_wordnet, inputs=[search_in], outputs=[search_out])
                
                with gr.Row():
                    # Left Column: Configuration
                    with gr.Column(scale=1):
                        with gr.Group():
                            gr.Markdown("**Dataset & Strategy**")
                            ds_name = gr.Dropdown(
                                ["ImageNet", "COCO", "Open Images", "Tencent ML-Images"], 
                                label="Source", 
                                value="ImageNet"
                            )
                            ds_info = gr.Markdown(
                                "_**ImageNet**: 21k classes. Best for general objects/animals._",
                                elem_id="ds-info"
                            )
                            ds_strategy = gr.Radio(
                                ["Standard", "Smart"],
                                label="Extraction Mode",
                                value="Standard",
                                info="Smart uses WordNet semantics to prune meaningless nodes."
                            )
                        
                        with gr.Group(visible=True) as ds_imagenet_group:
                            gr.Markdown("**ImageNet Configuration**")
                            ds_root = gr.Textbox(
                                label="Root Synset", 
                                value=config.get("datasets.imagenet.root_synset"),
                                placeholder="entity.n.01"
                            )
                            COMMON_ROOTS = {
                                "— Presets —": "",
                                "Everything": "entity.n.01",
                                "Animals": "animal.n.01",
                                "Living Things": "living_thing.n.01",
                                "Plants": "plant.n.02",
                                "Vehicles": "vehicle.n.01",
                                "Furniture": "furniture.n.01",
                                "Clothing": "clothing.n.01",
                                "Food": "food.n.01",
                                "Tools": "tool.n.01"
                            }
                            ds_presets = gr.Dropdown(
                                choices=list(COMMON_ROOTS.keys()),
                                label="Quick Presets"
                            )
                            def apply_preset(p):
                                return COMMON_ROOTS.get(p, "")
                            ds_presets.change(apply_preset, inputs=[ds_presets], outputs=[ds_root])
                        
                        with gr.Group():
                            gr.Markdown("**Hierarchy Depth**")
                            ds_depth = gr.Slider(1, 12, value=config.get("generation.default_depth"), step=1, label="Max Depth", info="Standard: hard limit. Smart: max ceiling.")
                        
                        with gr.Accordion("Smart Tuning Parameters", open=True, visible=False) as smart_tuning_group:
                            gr.Markdown("_Smart Mode uses WordNet to analyze semantic importance. Adjust these to control granularity._")
                            SMART_PRESETS = {
                                "Detailed": (6, 10, 3, False),
                                "Balanced": (4, 50, 5, False),
                                "Flat": (2, 500, 10, True)
                            }
                            ds_smart_preset = gr.Radio(list(SMART_PRESETS.keys()), label="Preset", value="Balanced")
                            ds_min_depth = gr.Slider(0, 10, value=4, step=1, label="Category Depth", info="Nodes shallower than this are kept as categories (lower = fewer distinct categories).")
                            ds_min_hyponyms = gr.Slider(0, 1000, value=50, step=10, label="Flattening Threshold", info="Nodes with more children than this are kept. Higher = more flattening of sub-lists.")
                            ds_min_leaf = gr.Slider(1, 100, value=5, step=1, label="Min Leaf Size", info="Minimum items to keep a list. Valid lists smaller than this are merged up.")
                            ds_merge_orphans = gr.Checkbox(label="Merge Orphans", value=False, info="If checked, small lists are merged into a 'misc' key in the parent; otherwise they are kept as-is.")
                            
                            def apply_smart_preset(p):
                                if p in SMART_PRESETS:
                                    return SMART_PRESETS[p]
                                return [gr.update()]*4                            
                            ds_smart_preset.change(apply_smart_preset, inputs=[ds_smart_preset], outputs=[ds_min_depth, ds_min_hyponyms, ds_min_leaf, ds_merge_orphans])
                        
                            ds_filter = gr.Dropdown(["none", "1k", "21k"], label="Sub-Filter", value="none")
                            ds_strict = gr.Checkbox(label="Strict Lexical Match", value=True)
                            ds_blacklist = gr.Checkbox(label="Hide Abstract Concepts", value=False)
                        
                        with gr.Group(visible=False) as ds_openimages_group:
                            ds_bbox_only = gr.Checkbox(label="Legacy BBox Mode (600 classes)", value=False, info="Use original bounding-box hierarchy instead of full 20k labels.")
                        
                        with gr.Row():
                            ds_glosses = gr.Checkbox(label="Include Instructions", value=True)
                            ds_out = gr.Textbox(label="Output Filename", value=update_ds_filename("ImageNet", config.get("datasets.imagenet.root_synset"), config.get("generation.default_depth"), "Standard", False))
                        
                        ds_btn = gr.Button("🚀 Generate Skeleton", variant="primary", size="lg")

                    # Right Column: Preview
                    with gr.Column(scale=1):
                        ds_file = gr.File(label="Download YAML")
                        ds_prev = gr.Code(language="yaml", label="Preview", lines=25)
                
                # Dynamic UI Linking
                def update_ds_ui(dataset_name, strategy):
                    is_imagenet = (dataset_name == "ImageNet")
                    can_use_smart = dataset_name in ["ImageNet", "Open Images", "Tencent ML-Images"]
                    is_smart = (strategy == "Smart") and can_use_smart
                    new_strategy = "Smart" if (can_use_smart and dataset_name != "ImageNet" and dataset_name != "COCO") else strategy
                    
                    return [
                        gr.update(visible=is_imagenet),                # ds_imagenet_group
                        gr.update(interactive=can_use_smart, value=new_strategy if not can_use_smart else strategy), # ds_strategy
                        gr.update(visible=is_smart),                   # smart_tuning_group
                        gr.update(visible=is_imagenet),                # adv_filter_group
                        gr.update(visible=(dataset_name == "Open Images")), # ds_openimages_group
                    ]
                    
                    # Update Info Text
                    info_map = {
                        "ImageNet": "_**ImageNet**: 21k classes. Best for general objects/animals._",
                        "COCO": "_**COCO**: 80 objects. Very small, flat list._",
                        "Open Images": "_**Open Images V7**: ~600 bbox classes or 20k+ image labels._",
                        "Tencent ML-Images": "_**Tencent ML**: 11k categories. Massive, modern coverage._"
                    }
                    info_text = info_map.get(dataset_name, "")
                
                ds_name.change(update_ds_ui, inputs=[ds_name, ds_strategy], outputs=[ds_imagenet_group, ds_strategy, smart_tuning_group, adv_filter_group, ds_openimages_group])
                ds_name.change(lambda x: ({
                    "ImageNet": "_**ImageNet**: 21k classes. Best for general objects/animals._",
                    "COCO": "_**COCO**: 80 objects. Very small, flat list._",
                    "Open Images": "_**Open Images V7**: ~600 bbox classes or 20k+ image labels._",
                    "Tencent ML-Images": "_**Tencent ML**: 11k categories. Massive, modern coverage._"
                }.get(x, "")), inputs=[ds_name], outputs=[ds_info])
                
                ds_strategy.change(update_ds_ui, inputs=[ds_name, ds_strategy], outputs=[ds_imagenet_group, ds_strategy, smart_tuning_group, adv_filter_group, ds_openimages_group])
                
                for comp in [ds_name, ds_root, ds_depth, ds_strategy, ds_bbox_only]:
                    comp.change(update_ds_filename, inputs=[ds_name, ds_root, ds_depth, ds_strategy, ds_bbox_only], outputs=[ds_out])
                
                ds_btn.click(
                    generate_dataset_handler, 
                    inputs=[ds_name, ds_strategy, ds_root, ds_depth, ds_out, ds_glosses, ds_filter, ds_strict, ds_blacklist, ds_min_depth, ds_min_hyponyms, ds_min_leaf, ds_merge_orphans, ds_bbox_only],
                    outputs=[ds_file, ds_prev]
                )

            # === TAB 2: CREATE (LLM) ===
            with gr.Tab("🪄 Create"):
                gr.Markdown("### Generate Taxonomy from Scratch — *LLM Powered*")
                with gr.Row():
                    with gr.Column():
                        cr_topic = gr.Textbox(label="Topic", placeholder="e.g. Types of Cyberpunk Augmentations", info="The LLM will brainstorm a logical hierarchy.")
                        cr_out = gr.Textbox(label="Output Filename", value="topic_skeleton.yaml")
                        cr_topic.change(update_cr_filename, inputs=[cr_topic], outputs=[cr_out])
                        cr_btn = gr.Button("✨ Generate", variant="primary")
                    with gr.Column():
                        cr_file = gr.File(label="Download YAML")
                        cr_prev = gr.Code(language="yaml", label="Preview", lines=20)
                cr_btn.click(create_handler, inputs=[cr_topic, model_state, api_key_state, cr_out], outputs=[cr_file, cr_prev])

            # === TAB 3: CATEGORIZE (LLM) ===
            with gr.Tab("📊 Categorize"):
                gr.Markdown("### Organize Flat List into Hierarchy — *LLM Powered*")
                with gr.Row():
                    with gr.Column():
                        cat_terms = gr.TextArea(label="Raw Terms", placeholder="Lion\\nTiger\\nLeopard\\n...", info="Paste one item per line. LLM will create structure.")
                        cat_out = gr.Textbox(label="Output Filename", value="categorized.yaml")
                        cat_terms.change(update_cat_filename, inputs=[cat_terms], outputs=[cat_out])
                        cat_btn = gr.Button("🗂️ Categorize", variant="primary")
                    with gr.Column():
                        cat_file = gr.File(label="Download YAML")
                        cat_prev = gr.Code(language="yaml", label="Preview", lines=20)
                cat_btn.click(categorize_handler, inputs=[cat_terms, model_state, api_key_state, cat_out], outputs=[cat_file, cat_prev])

            # === TAB 4: ENRICH (LLM) ===
            with gr.Tab("✨ Enrich"):
                gr.Markdown("### Add Instructions to Existing YAML — *LLM Powered*")
                with gr.Row():
                    with gr.Column():
                        en_yaml = gr.TextArea(label="Existing YAML", placeholder="Paste your .yaml structure here...", info="LLM will add '# instruction:' comments.")
                        en_topic = gr.Textbox(label="Context / Goal", value="AI image generation wildcards")
                        en_out = gr.Textbox(label="Output Filename", value="enriched.yaml")
                        en_topic.change(update_en_filename, inputs=[en_topic], outputs=[en_out])
                        en_btn = gr.Button("💡 Enrich", variant="primary")
                    with gr.Column():
                        en_file = gr.File(label="Download YAML")
                        en_prev = gr.Code(language="yaml", label="Preview", lines=20)
                en_btn.click(enrich_handler, inputs=[en_yaml, en_topic, model_state, api_key_state, en_out], outputs=[en_file, en_prev])

            # === TAB 5: SETTINGS ===
            with gr.Tab("⚙️ Settings"):
                gr.Markdown("### Configuration")
                with gr.Group():
                    gr.Markdown("**API Key** — *Required for LLM tabs (Create, Categorize, Enrich)*")
                    set_key = gr.Textbox(label="OpenRouter API Key", value=initial_key, type="password")
                    set_save_key = gr.Button("Update API Key")
                    
                    def update_api_key(new_key):
                        status = f"🔑 API: {'✅ Set' if new_key else '❌ Not Set'}"
                        return new_key, status
                    
                    set_save_key.click(update_api_key, inputs=[set_key], outputs=[api_key_state, api_status])
                
                with gr.Group():
                    gr.Markdown("**Default LLM Model**")
                    set_model = gr.Dropdown(
                        [config.model, "anthropic/claude-3.5-sonnet", "openai/gpt-4o", "google/gemini-pro"], 
                        label="Model", 
                        value=config.model, 
                        allow_custom_value=True,
                        info="Used for all LLM-powered features."
                    )
                    set_save_model = gr.Button("Update Model")
                    set_save_model.click(lambda m: m, inputs=[set_model], outputs=[model_state])
                
                gr.Markdown("> *Settings are for this session only. Edit `wildcards-gen.yaml` for persistence.*")

    server_name = config.get("gui.server_name")
    server_port = config.get("gui.server_port")
    demo.launch(share=share, server_name=server_name, server_port=server_port)

