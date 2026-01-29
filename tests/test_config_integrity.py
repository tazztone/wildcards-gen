import unittest
from wildcards_gen.core.presets import SMART_PRESETS, DATASET_PRESET_OVERRIDES

class TestConfigIntegrity(unittest.TestCase):
    def test_smart_presets_within_bounds(self):
        """Verify SMART_PRESETS values don't exceed slider limits."""
        # Slider Max Limits from gui.py
        MAX_DEPTH = 10
        MAX_HYPONYMS = 2000 # Raised from 1000 in recent fix
        MAX_LEAF = 100
        
        for name, values in SMART_PRESETS.items():
            depth, hyp, leaf, orphan, clean, arrange = values
            self.assertLessEqual(depth, MAX_DEPTH, f"Preset {name} depth {depth} > {MAX_DEPTH}")
            self.assertLessEqual(hyp, MAX_HYPONYMS, f"Preset {name} hyponyms {hyp} > {MAX_HYPONYMS}")
            self.assertLessEqual(leaf, MAX_LEAF, f"Preset {name} leaf {leaf} > {MAX_LEAF}")

    def test_dataset_overrides_integrity(self):
        """Verify DATASET_PRESET_OVERRIDES match strict schema."""
        MAX_DEPTH = 10
        MAX_HYPONYMS = 2000
        MAX_LEAF = 100
        
        for ds_name, presets in DATASET_PRESET_OVERRIDES.items():
            for p_name, values in presets.items():
                depth, hyp, leaf, orphan, clean, arrange = values
                self.assertLessEqual(depth, MAX_DEPTH, f"Override {ds_name}:{p_name} depth {depth} > {MAX_DEPTH}")
                self.assertLessEqual(hyp, MAX_HYPONYMS, f"Override {ds_name}:{p_name} hyponyms {hyp} > {MAX_HYPONYMS}")
                self.assertLessEqual(leaf, MAX_LEAF, f"Override {ds_name}:{p_name} leaf {leaf} > {MAX_LEAF}")

if __name__ == '__main__':
    unittest.main()
