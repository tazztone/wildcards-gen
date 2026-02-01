import unittest
import os
import shutil
import tempfile
import json
from ruamel.yaml.comments import CommentedMap
from wildcards_gen.core.structure import StructureManager

class TestStructureExtended(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.mgr = StructureManager()

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_jsonl_export(self):
        # Create sample data
        data = CommentedMap()
        data['animal'] = CommentedMap()
        data['animal']['dog'] = ['beagle', 'poodle']
        data['vehicle'] = ['car']
        
        output_path = os.path.join(self.test_dir, "test.jsonl")
        
        # Save as JSONL
        self.mgr.save_structure(data, output_path, format='jsonl')
        
        self.assertTrue(os.path.exists(output_path))
        
        # Read back
        lines = []
        with open(output_path, 'r', encoding='utf-8') as f:
            for line in f:
                lines.append(json.loads(line))
                
        # Expect 3 lines (beagle, poodle, car)
        self.assertEqual(len(lines), 3)
        
        # Verify content
        beagle = next(l for l in lines if l['text'] == 'beagle')
        self.assertEqual(beagle['label'], 'dog')
        self.assertEqual(beagle['hierarchy'], ['animal', 'dog'])
        
        car = next(l for l in lines if l['text'] == 'car')
        self.assertEqual(car['label'], 'vehicle')
        self.assertEqual(car['hierarchy'], ['vehicle'])

if __name__ == '__main__':
    unittest.main()