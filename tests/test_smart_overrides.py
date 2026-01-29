
import unittest
from wildcards_gen.core.smart import SmartConfig

class TestSmartOverrides(unittest.TestCase):
    def setUp(self):
        self.overrides = {
            "dog": {"min_hyponyms": 100},
            "n12345678": {"min_depth": 20},
            "cat": {"merge_orphans": True}
        }
        self.config = SmartConfig(
            enabled=True, 
            min_depth=5, 
            min_hyponyms=10, 
            merge_orphans=False,
            category_overrides=self.overrides
        )

    def test_no_override(self):
        """Should return self if no override matches."""
        child = self.config.get_child_config("bird", "n99999999")
        self.assertEqual(child.min_hyponyms, 10)
        self.assertEqual(child.min_depth, 5)

    def test_override_by_name(self):
        """Should apply override by name."""
        child = self.config.get_child_config("dog", "n00000001")
        self.assertEqual(child.min_hyponyms, 100) # Overridden
        self.assertEqual(child.min_depth, 5) # Default preserved

    def test_override_by_wnid(self):
        """Should apply override by WNID."""
        child = self.config.get_child_config("random_thing", "n12345678")
        self.assertEqual(child.min_depth, 20) # Overridden
        self.assertEqual(child.min_hyponyms, 10) # Default

    def test_wnid_priority(self):
        """WNID should take precedence over name if both exist."""
        # Setup: name 'dog' has min_hyponyms=100
        # Add WNID override for same node
        self.config.category_overrides["n_dog_id"] = {"min_hyponyms": 500}
        
        child = self.config.get_child_config("dog", "n_dog_id")
        self.assertEqual(child.min_hyponyms, 500)

    def test_case_insensitive_name(self):
        """Should match name case-insensitively."""
        child = self.config.get_child_config("DOG", "n00000001")
        self.assertEqual(child.min_hyponyms, 100)

    def test_propagate_overrides(self):
        """Child config should retain the overrides map."""
        child = self.config.get_child_config("dog", "n00000001")
        self.assertEqual(child.category_overrides, self.overrides)
        
        # Grandchild checking
        grandchild = child.get_child_config("cat", "n_cat_id")
        self.assertTrue(grandchild.merge_orphans)

    def test_recursive_override_behavior(self):
        """
        When an override changes a value, that value becomes the new default 
        for the subtree (because we pass the modified config down).
        """
        # "dog" changes min_hyponyms to 100
        dog_config = self.config.get_child_config("dog", "n_dog_id")
        self.assertEqual(dog_config.min_hyponyms, 100)
        
        # "poodle" (child of dog) should inherit 100 if it has no specific override
        poodle_config = dog_config.get_child_config("poodle", "n_poodle_id")
        self.assertEqual(poodle_config.min_hyponyms, 100)

if __name__ == '__main__':
    unittest.main()
