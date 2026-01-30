
import os
import csv
import logging
from unittest.mock import patch, MagicMock
from wildcards_gen.core.datasets.tencent import generate_tencent_hierarchy
from wildcards_gen.core.structure import StructureManager

# Setup logger
logging.basicConfig(level=logging.INFO)

# Create dummy hierarchy file
HIERARCHY_FILE = "tests/data/dummy_tencent.csv"
os.makedirs("tests/data", exist_ok=True)

def create_dummy_data():
    # ID, Name, ParentID
    # format: index, id, parent_idx, name
    data = [
        ["0", "n00000000", "-1", "Entity"],
        ["1", "n00000001", "0", "physical entity"], # Wrapper to skip
        ["2", "n00000002", "1", "object"],          # Wrapper to skip (if in skip list)
        ["3", "n00000003", "2", "animal"],
        ["4", "n00000004", "3", "bird"],
        ["15", "n00000004b", "3", "fish"], # Sibling to bird to keep animal
        # Add enough birds to trigger clustering/arrangement if embeddings work
        # We might need to mock clustering if we don't have embeddings for these specific fake names
        # But we can try using real names that have embeddings
        ["5", "n01503061", "4", "eagle"], 
        ["6", "n01503062", "4", "hawk"],
        ["7", "n01503063", "4", "falcon"],
        ["8", "n01503064", "4", "sparrow"],
        ["9", "n01503065", "4", "finch"],
        ["10", "n01503066", "4", "robin"],
        ["11", "n01503067", "4", "owl"],
        ["16", "n01503061b", "15", "goldfish"],
        ["17", "n01503062b", "15", "shark"],
        ["12", "n00000005", "2", "misc_container"],
        ["13", "n00000006", "12", "orphan_1"],
        ["14", "n00000007", "12", "orphan_2"]
    ]
    
    with open(HIERARCHY_FILE, "w", newline="") as f:
        writer = csv.writer(f, delimiter='\t')
        writer.writerow(["Index", "ID", "ParentIndex", "Name"])
        writer.writerows(data)

def run_verification():
    create_dummy_data()
    
    # Mock download to return our file
    with patch('wildcards_gen.core.datasets.tencent.download_tencent_hierarchy', return_value=HIERARCHY_FILE):
        # Mock embeddings to force clustering?
        # Or just rely on standard arranging if model exists.
        # Let's try running with smart=True and see what happens.
        # We need to make sure 'object' and 'physical entity' are pruned.
        
        # We need to mock 'check_dependencies' to be True if we want smart mode
     # Helper to create mock with name attribute
     def create_synset_mock(w):
         m = MagicMock()
         m.name = w
         m.definition.return_value = f"Def of {w}"
         return m

     with patch('wildcards_gen.core.linter.check_dependencies', return_value=True):
         with patch('wildcards_gen.core.datasets.tencent.get_synset_from_wnid', side_effect=create_synset_mock):
             with patch('wildcards_gen.core.smart.should_prune_node') as mock_prune:
                 # Define pruning logic based on mocked synset name (which is the wnid)
                 def prune_side_effect(synset, child_count, is_root, config):
                     print(f"DEBUG: prune check {getattr(synset, 'name', 'None')} count={child_count}")
                     if not synset: return True
                     wnid = synset.name # We set this in the lambda above
                     # Keep 'animal' (n00000003)
                     if wnid == 'n00000003': return False
                     # Prune 'misc_container' (n00000005) -> Flattens to orphans
                     if wnid == 'n00000005': return True
                     # Prune 'object' (n00000002) -> Flattens to bubble up children
                     if wnid == 'n00000002': return True
                     # Keep 'physical entity' (n00000001) -> Valid category
                     if wnid == 'n00000001': return False
                     return False
                 
                 mock_prune.side_effect = prune_side_effect

                 hierarchy = generate_tencent_hierarchy(
                     smart=True,
                     merge_orphans=True, # To test misc renaming
                     with_glosses=True,
                     semantic_arrangement=False # Disable arrangement for simple structural test first
                     # Or enable it to test the full stack if we trust mocks
                 )
             
             sm = StructureManager()
             yaml_str = sm.to_string(hierarchy)
             
             print("\n--- Generated YAML ---")
             print(yaml_str)
             print("----------------------\n")
             
             # Assertions
             if "object" in yaml_str:
                 print("FAILED: 'object' wrapper was NOT pruned.")
             else:
                 print("PASSED: 'object' wrapper was pruned.")
                 
             if "# instruction: Miscellaneous" in yaml_str:
                 print("PASSED: Misc instruction present.")
             else:
                 print("FAILED: Misc instruction missing.")
                 
             if "other_misc_container" in yaml_str or "other_" in yaml_str:
                 print("PASSED: 'other_{}' naming used (orphans_label_template).")
             else:
                 print("FAILED: 'misc' renaming didn't happen (check if triggered).")

             # Test Smart Arrangement manually
             # We forced semantic_arrangement=False above.
             # Now let's try calling apply_semantic_arrangement directly via test to ensure instructions mock worked?
             # Actually, unit tests covered that somewhat.
             
             
if __name__ == "__main__":
    run_verification()
