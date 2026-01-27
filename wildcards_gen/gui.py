
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

def update_ds_filename(name, root, depth):
    root_part = clean_filename(root.split('.')[0]) if '.' in root else clean_filename(root)
    name_part = clean_filename(name)
    return f"{name_part}_{root_part}_d{depth}.yaml" if root_part else f"{name_part}_d{depth}.yaml"

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

def generate_dataset_handler(dataset_name, root, depth, output_name):
    try:
        if dataset_name == "ImageNet":
            if not root:
                return None, "Error: Root synset required for ImageNet (e.g. animal.n.01)"
            data = imagenet.generate_imagenet_tree(root, max_depth=int(depth))
        elif dataset_name == "COCO":
            data = coco.generate_coco_hierarchy()
        elif dataset_name == "Open Images":
            data = openimages.generate_openimages_hierarchy(max_depth=int(depth))
        elif dataset_name == "Tencent ML-Images":
            data = tencent.generate_tencent_hierarchy(max_depth=int(depth))
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
        gr.Markdown("# 🎴 Wildcards-Gen")
        gr.Markdown("Unified toolkit for hierarchical skeleton generation.")
        
        api_key_state = gr.State(initial_key)
        
        with gr.Tabs():
            # TABS 1: DATASETS
            with gr.Tab("🗂️ Datasets"):
                gr.Markdown("### Generate from Computer Vision Datasets (Local & Free)")
                with gr.Row():
                    with gr.Column():
                        ds_name = gr.Dropdown(
                            ["ImageNet", "COCO", "Open Images", "Tencent ML-Images"], 
                            label="Dataset Source", 
                            value="ImageNet",
                            info="Select a computer vision dataset. These are processed locally and do not require an API key."
                        )
                        ds_root = gr.Textbox(
                            label="Root Synset (WordNet ID)", 
                            value=config.get("datasets.imagenet.root_synset"),
                            info="The ID to start from. Use the Search Tool below to find IDs.",
                            placeholder="entity.n.01"
                        )
                        
                        COMMON_ROOTS = {
                            "Select a preset...": "",
                            "Everything (Universal Root)": "entity.n.01",
                            "Living Things": "living_thing.n.01",
                            "Animals": "animal.n.01",
                            "Plants": "plant.n.02",
                            "Vehicles": "vehicle.n.01",
                            "Furniture": "furniture.n.01",
                            "Clothing": "clothing.n.01",
                            "Food": "food.n.01",
                            "Tools": "tool.n.01",
                            "Buildings": "dwelling.n.01",
                            "Musical Instruments": "musical_instrument.n.01"
                        }
                        
                        ds_presets = gr.Dropdown(
                            choices=list(COMMON_ROOTS.keys()),
                            label="Common Root Presets",
                            info="Quickly populate the Root Synset with popular categories."
                        )
                        
                        def apply_preset(preset_name):
                            return COMMON_ROOTS.get(preset_name, "")
                        
                        ds_presets.change(apply_preset, inputs=[ds_presets], outputs=[ds_root])

                        ds_depth = gr.Slider(
                            1, 10, 
                            value=config.get("generation.default_depth"), 
                            step=1, 
                            label="Recursion Depth",
                            info="How many levels of the hierarchy to extract. Depth 3-5 is usually ideal."
                        )
                        ds_out = gr.Textbox(
                            label="Output Filename", 
                            value=update_ds_filename("ImageNet", config.get("datasets.imagenet.root_synset"), config.get("generation.default_depth")),
                            info=f"Saved to: {config.output_dir}"
                        )
                        
                        # Link changes
                        for comp in [ds_name, ds_root, ds_depth]:
                            comp.change(update_ds_filename, inputs=[ds_name, ds_root, ds_depth], outputs=[ds_out])
                        
                        ds_btn = gr.Button("Generate Dataset", variant="primary")
                        
                        gr.Markdown("---")
                        gr.Markdown("### 🔍 WordNet ID Search")
                        gr.Markdown("Not sure which ID to use? Search for a word here.")
                        with gr.Row():
                            search_in = gr.Textbox(label="Search Term", placeholder="e.g. camera, dog, sword")
                            search_btn = gr.Button("Search WordNet")
                        search_out = gr.Markdown("Results will appear here...")
                        
                        search_btn.click(search_wordnet, inputs=[search_in], outputs=[search_out])
                    with gr.Column():
                        ds_file = gr.File(label="Download YAML")
                        ds_prev = gr.Code(language="yaml", label="Preview")
                
                ds_btn.click(
                    generate_dataset_handler, 
                    inputs=[ds_name, ds_root, ds_depth, ds_out], 
                    outputs=[ds_file, ds_prev]
                )

            # TAB 2: CREATE
            with gr.Tab("🪄 Create"):
                gr.Markdown("### Generate Taxonomy from Scratch (LLM Powered)")
                with gr.Row():
                    with gr.Column():
                        cr_topic = gr.Textbox(
                            label="Taxonomy Topic", 
                            placeholder="e.g. Types of Cyberpunk Augmentations or Victorian Fashion",
                            info="Describe the subject. The LLM will brainstorm a logical hierarchy for it."
                        )
                        cr_model = gr.Dropdown(
                            [config.model, "anthropic/claude-3.5-sonnet", "openai/gpt-4o"], 
                            label="Model Selection", 
                            value=config.model, 
                            allow_custom_value=True,
                            info="Choose which LLM processes your request. Free models are usually sufficient."
                        )
                        cr_out = gr.Textbox(
                            label="Output Filename", 
                            value="topic_skeleton.yaml",
                            info=f"Saved to: {config.output_dir}"
                        )
                        cr_topic.change(update_cr_filename, inputs=[cr_topic], outputs=[cr_out])
                        
                        cr_btn = gr.Button("Generate from Scratch", variant="primary")
                    with gr.Column():
                        cr_file = gr.File(label="Download YAML")
                        cr_prev = gr.Code(language="yaml", label="Preview")
                
                cr_btn.click(
                    create_handler, 
                    inputs=[cr_topic, cr_model, api_key_state, cr_out], 
                    outputs=[cr_file, cr_prev]
                )

            # TAB 3: CATEGORIZE
            with gr.Tab("📊 Categorize"):
                gr.Markdown("### Organize Flat Term List into Hierarchy (LLM Powered)")
                with gr.Row():
                    with gr.Column():
                        cat_terms = gr.TextArea(
                            label="Raw Terms", 
                            placeholder="Lion\nTiger\nLeopard\n...",
                            info="Paste a flat list of items (one per line). The LLM will create a structure and sort them."
                        )
                        cat_model = gr.Dropdown(
                            [config.model, "anthropic/claude-3.5-sonnet"], 
                            label="Model Selection", 
                            value=config.model, 
                            allow_custom_value=True,
                            info="High-reasoning models (like Sonnet) are better for complex sorting."
                        )
                        cat_out = gr.Textbox(
                            label="Output Filename", 
                            value="categorized.yaml",
                            info=f"Saved to: {config.output_dir}"
                        )
                        cat_terms.change(update_cat_filename, inputs=[cat_terms], outputs=[cat_out])
                        
                        cat_btn = gr.Button("Categorize Terms", variant="primary")
                    with gr.Column():
                        cat_file = gr.File(label="Download YAML")
                        cat_prev = gr.Code(language="yaml", label="Preview")
                
                cat_btn.click(
                    categorize_handler, 
                    inputs=[cat_terms, cat_model, api_key_state, cat_out], 
                    outputs=[cat_file, cat_prev]
                )

            # TAB 4: ENRICH
            with gr.Tab("✨ Enrich"):
                gr.Markdown("### Add Instructions to Existing YAML (LLM Powered)")
                with gr.Row():
                    with gr.Column():
                        en_yaml = gr.TextArea(
                            label="Existing YAML Content", 
                            placeholder="Paste your .yaml structure here...",
                            info="The LLM will scan your keys and add or improve '# instruction:' comments."
                        )
                        en_topic = gr.Textbox(
                            label="Context / Instruction Goal", 
                            value="AI image generation wildcards",
                            info="Optional context to help the LLM generate more relevant instructions."
                        )
                        en_model = gr.Dropdown(
                            [config.model], 
                            label="Model Selection", 
                            value=config.model, 
                            allow_custom_value=True,
                            info="Model used to generate descriptions."
                        )
                        en_out = gr.Textbox(
                            label="Output Filename", 
                            value="enriched.yaml",
                            info=f"Saved to: {config.output_dir}"
                        )
                        en_topic.change(update_en_filename, inputs=[en_topic], outputs=[en_out])
                        
                        en_btn = gr.Button("Enrich Instructions", variant="primary")
                    with gr.Column():
                        en_file = gr.File(label="Download YAML")
                        en_prev = gr.Code(language="yaml", label="Preview")
                
                en_btn.click(
                    enrich_handler, 
                    inputs=[en_yaml, en_topic, en_model, api_key_state, en_out], 
                    outputs=[en_file, en_prev]
                )

            # TAB 5: SETTINGS
            with gr.Tab("⚙️ Settings"):
                gr.Markdown("### Session Settings")
                gr.Markdown("Update your credentials and session parameters. These override environment variables for this session.")
                set_key = gr.Textbox(
                    label="OpenRouter API Key", 
                    value=initial_key, 
                    type="password",
                    info="Used for Create, Categorize, and Enrich tabs. Not needed for Datasets."
                )
                set_save = gr.Button("Update API Key")
                
                def update_api_key(new_key):
                    return new_key
                
                set_save.click(update_api_key, inputs=[set_key], outputs=[api_key_state])
                gr.Markdown("> Note: Settings applied here are persistent for this browser session only. To make them permanent, edit `wildcards-gen.yaml`.")

    server_name = config.get("gui.server_name")
    server_port = config.get("gui.server_port")
    demo.launch(share=share, server_name=server_name, server_port=server_port)
