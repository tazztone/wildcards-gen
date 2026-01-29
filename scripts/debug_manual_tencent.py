
import logging
from wildcards_gen.core.datasets.tencent import generate_tencent_hierarchy
from wildcards_gen.core.smart import SmartConfig
from ruamel.yaml import YAML
import sys

# Configure logging to see debug output
logging.basicConfig(level=logging.DEBUG)

def debug_run():
    print("🚀 Starting Manual Tencent Debug Run...")
    
    # Simulate GUI/CLI arguments
    hierarchy = generate_tencent_hierarchy(
        max_depth=5,
        with_glosses=True,
        smart=True,
        semantic_arrangement=True,
        semantic_arrangement_method="eom",
        debug_arrangement=True
    )
    
    print("\n✅ Generation Complete.")
    
    # Check output
    if not hierarchy:
        print("❌ Error: Hierarchy is empty!")
        return

    print(f"📦 Generated {len(hierarchy)} top-level categories.")
    
    # Print a sample
    yaml = YAML()
    print("\n--- Hierarchy Sample (First 20 lines) ---")
    yaml.dump(hierarchy, sys.stdout)

if __name__ == "__main__":
    try:
        debug_run()
    except Exception as e:
        print(f"\n❌ FAILED with error: {e}")
        import traceback
        traceback.print_exc()
