
import gradio as gr
import os
import yaml
from wildcards_gen.core.datasets import imagenet, coco, openimages, tencent
from wildcards_gen.core.structure import StructureManager

def generate_dataset(dataset_name, root, depth, output_name):
    """Generate dataset and return file path + content."""
    
    mgr = StructureManager()
    data = {}
    
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
            
        # Convert to string
        yaml_str = mgr.to_string(data)
        
        # Save to file
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        if not output_name.endswith(".yaml"):
            output_name += ".yaml"
        output_path = os.path.join(output_dir, output_name)
        
        with open(output_path, "w") as f:
            f.write(yaml_str)
            
        return output_path, yaml_str
        
    except Exception as e:
        return None, f"Error: {str(e)}"

def launch_gui(share=False):
    with gr.Blocks(title="Wildcards-Gen") as demo:
        gr.Markdown("# Wildcards-Gen Structure Creator")
        gr.Markdown("Generate hierarchical YAML skeletons for wildcards-generator.")
        
        with gr.Row():
            with gr.Column():
                dataset = gr.Dropdown(["ImageNet", "COCO", "Open Images", "Tencent ML-Images"], label="Dataset", value="ImageNet")
                root = gr.Textbox(label="Root Synset (ImageNet only)", value="animal.n.01", placeholder="e.g. musical_instrument.n.01")
                depth = gr.Slider(minimum=1, maximum=10, value=3, step=1, label="Depth")
                filename = gr.Textbox(label="Output Filename", value="skeleton.yaml")
                btn = gr.Button("Generate structure", variant="primary")
                
            with gr.Column():
                output_file = gr.File(label="Download YAML")
                preview = gr.Code(language="yaml", label="Preview")
        
        btn.click(
            generate_dataset, 
            inputs=[dataset, root, depth, filename], 
            outputs=[output_file, preview]
        )
        
    demo.launch(share=share)
