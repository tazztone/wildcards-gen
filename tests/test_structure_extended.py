
import unittest
import logging
import os
import shutil
from wildcards_gen.core.structure import StructureManager
from ruamel.yaml.comments import CommentedMap, CommentedSeq

class TestStructureExtended(unittest.TestCase):
    def setUp(self):
        self.sm = StructureManager()
        self.test_dir = "tests/data_extended"
        os.makedirs(self.test_dir, exist_ok=True)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_deeply_nested_structure(self):
        """Verify comments are preserved in deep nesting."""
        root = self.sm.create_empty_structure()
        self.sm.add_category_with_instruction(root, "LEVEL1", "Root level")

        self.sm.add_category_with_instruction(root["LEVEL1"], "LEVEL2", "Second level")
        self.sm.add_category_with_instruction(root["LEVEL1"]["LEVEL2"], "LEVEL3", "Third level")

        self.sm.add_leaf_list(root["LEVEL1"]["LEVEL2"]["LEVEL3"], "ITEMS", ["a", "b"], "Leaf items")

        yaml_str = self.sm.to_string(root)

        self.assertIn("# instruction: Root level", yaml_str)
        self.assertIn("# instruction: Second level", yaml_str)
        self.assertIn("# instruction: Third level", yaml_str)
        self.assertIn("# instruction: Leaf items", yaml_str)

        # Check indentation structure implicitly by parsing
        # But we also want to ensure the visual structure is as expected
        lines = yaml_str.splitlines()
        # LEVEL1 is top level
        self.assertTrue(any(line.startswith("LEVEL1:") for line in lines))
        # LEVEL2 should be indented
        self.assertTrue(any(line.strip().startswith("LEVEL2:") and line.startswith("  ") for line in lines))
        # LEVEL3 should be more indented
        self.assertTrue(any(line.strip().startswith("LEVEL3:") and line.startswith("    ") for line in lines))

    def test_special_characters(self):
        """Test keys and values with special characters."""
        root = self.sm.create_empty_structure()
        special_key = "Category: Subtitle"
        quoted_key = 'Category "Quoted"'
        unicode_item = "ümlaut"

        self.sm.add_leaf_list(root, special_key, [unicode_item], "Special chars test")
        self.sm.add_category_with_instruction(root, quoted_key, "Quotes test")

        yaml_str = self.sm.to_string(root)

        # Check if keys are present (handling quoting if necessary)
        self.assertIn("Category: Subtitle", yaml_str)
        self.assertIn('Category "Quoted"', yaml_str)
        self.assertIn(unicode_item, yaml_str)

        # Parse back to ensure validity
        loaded = self.sm.from_string(yaml_str)
        self.assertIn(special_key, loaded)
        self.assertIn(quoted_key, loaded)
        self.assertIn(unicode_item, loaded[special_key])

    def test_formatting_constraints(self):
        """Verify exact indentation rules."""
        root = self.sm.create_empty_structure()
        self.sm.add_leaf_list(root, "my_list", ["item1", "item2"], "my instruction")

        yaml_str = self.sm.to_string(root)

        # Expected format:
        # my_list:  # instruction: my instruction
        #   - item1
        #   - item2

        lines = yaml_str.splitlines()
        self.assertTrue(lines[0].startswith("my_list:"))
        self.assertIn("# instruction: my instruction", lines[0])
        self.assertTrue(lines[1].startswith("  - item1"))
        self.assertTrue(lines[2].startswith("  - item2"))

    def test_merge_conflict_resolution(self):
        """Test merge logic with conflicts."""
        # Case 1: Existing is list, Incoming is dict -> Warning and Skip
        root = self.sm.create_empty_structure()
        self.sm.add_leaf_list(root, "conflict_key", ["item1"], "list instruction")

        incoming = {"conflict_key": {"subkey": "val"}}

        with self.assertLogs("wildcards_gen.core.structure", level="WARNING") as cm:
            self.sm.merge_categorized_data(root, incoming)

        self.assertTrue(any("Conflict at 'conflict_key'" in log for log in cm.output))
        self.assertIsInstance(root["conflict_key"], (list, CommentedSeq))

        # Case 2: Existing is dict, Incoming is list -> Warning and Skip
        root2 = self.sm.create_empty_structure()
        self.sm.add_category_with_instruction(root2, "conflict_key", "dict instruction")

        incoming2 = {"conflict_key": ["item1"]}

        with self.assertLogs("wildcards_gen.core.structure", level="WARNING") as cm:
            self.sm.merge_categorized_data(root2, incoming2)

        self.assertTrue(any("Conflict at 'conflict_key'" in log for log in cm.output))
        self.assertIsInstance(root2["conflict_key"], (dict, CommentedMap))

    def test_round_trip_consistency(self):
        """Test saving and loading preserves structure and comments."""
        root = self.sm.create_empty_structure()
        self.sm.add_category_with_instruction(root, "CAT1", "Instruction 1")
        self.sm.add_leaf_list(root["CAT1"], "LIST1", ["item1"], "Instruction 2")

        file_path = os.path.join(self.test_dir, "round_trip.yaml")
        self.sm.save_structure(root, file_path)

        loaded = self.sm.load_structure(file_path)

        # Modify nothing, save again
        file_path_2 = os.path.join(self.test_dir, "round_trip_2.yaml")
        self.sm.save_structure(loaded, file_path_2)

        with open(file_path, 'r') as f1, open(file_path_2, 'r') as f2:
            self.assertEqual(f1.read(), f2.read())

    def test_spa_compatibility(self):
        """
        Verify the generated structure complies with SPA requirements.
        1. Top level keys are categories.
        2. Values are either categories (dict) or leaf lists (list).
        3. Leaf lists contain strings.
        4. Every category (dict key) has an instruction comment.
        """
        root = self.sm.create_empty_structure()
        self.sm.add_category_with_instruction(root, "CAT", "instr")
        self.sm.add_leaf_list(root["CAT"], "LEAF", ["val"], "instr2")

        # Helper to validate node
        def validate_node(node, path="root"):
            if isinstance(node, (dict, CommentedMap)):
                for key, value in node.items():
                    # Check for instruction comment
                    # Ruamel stores comments in .ca attribute
                    # This is a bit internal, but we can check if it exists in the output string
                    # Alternatively, check structure types

                    if isinstance(value, (dict, CommentedMap)):
                        validate_node(value, f"{path}.{key}")
                    elif isinstance(value, (list, CommentedSeq)):
                         for item in value:
                             if not isinstance(item, str):
                                 raise AssertionError(f"Item in {path}.{key} is not a string: {item}")
                    else:
                        raise AssertionError(f"Value at {path}.{key} has invalid type: {type(value)}")
            else:
                raise AssertionError(f"Node at {path} is not a dict: {type(node)}")

        validate_node(root)

        # Verify instructions exist in output
        yaml_str = self.sm.to_string(root)
        self.assertIn("# instruction: instr", yaml_str)
        self.assertIn("# instruction: instr2", yaml_str)

if __name__ == '__main__':
    unittest.main()
