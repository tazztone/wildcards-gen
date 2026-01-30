
import os
import unittest
import shutil
from wildcards_gen.core.structure import StructureManager

class TestStructureManager(unittest.TestCase):
    def setUp(self):
        self.sm = StructureManager()
        self.test_dir = "tests/data"
        self.test_file = os.path.join(self.test_dir, "test_structure.yaml")
        os.makedirs(self.test_dir, exist_ok=True)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_add_category_with_instruction(self):
        root = self.sm.create_empty_structure()
        self.sm.add_category_with_instruction(root, "ANIMALS", "living creatures")

        # Verify in memory
        self.assertIn("ANIMALS", root)

        # Verify serialized string contains comment
        yaml_str = self.sm.to_string(root)
        self.assertIn("ANIMALS:", yaml_str)
        self.assertIn("# instruction: living creatures", yaml_str)

    def test_add_leaf_list(self):
        root = self.sm.create_empty_structure()
        self.sm.add_leaf_list(root, "FRUITS", ["apple", "banana"], "edible plants")
        
        self.assertIn("FRUITS", root)
        self.assertEqual(root["FRUITS"], ["apple", "banana"])
        
        yaml_str = self.sm.to_string(root)
        self.assertIn("# instruction: edible plants", yaml_str)
        self.assertIn("- apple", yaml_str)

    def test_save_and_load(self):
        root = self.sm.create_empty_structure()
        self.sm.add_category_with_instruction(root, "VEHICLES", "machines for transport")
        self.sm.add_leaf_list(root["VEHICLES"], "CARS", ["sedan", "suv"], "4 wheels")

        self.sm.save_structure(root, self.test_file)

        loaded = self.sm.load_structure(self.test_file)
        self.assertIn("VEHICLES", loaded)
        self.assertIn("CARS", loaded["VEHICLES"])

        # Check if comments persisted
        with open(self.test_file, 'r') as f:
            content = f.read()
            self.assertIn("# instruction: machines for transport", content)
            self.assertIn("# instruction: 4 wheels", content)

    def test_round_trip_persistence(self):
        root = self.sm.create_empty_structure()
        self.sm.add_category_with_instruction(root, "PLANTS", "green things")
        self.sm.save_structure(root, self.test_file)
        
        # Load back
        loaded = self.sm.load_structure(self.test_file)
        self.assertIn("PLANTS", loaded)
        
        # Modify
        self.sm.add_leaf_list(loaded["PLANTS"], "TREES", ["oak", "pine"], "tall plants")
        
        # Save again
        self.sm.save_structure(loaded, self.test_file)
        
        # Load again and verify BOTH instructions exist
        with open(self.test_file, 'r') as f:
            content = f.read()
            self.assertIn("# instruction: green things", content)
            self.assertIn("# instruction: tall plants", content)

if __name__ == "__main__":
    unittest.main()
