"""
Import Walker Test.

Traverses the wildcards_gen package and attempts to import every module.
catches syntax errors/missing deps early.
"""
import unittest
import pkgutil
import importlib
import wildcards_gen

class TestImportsWalk(unittest.TestCase):
    def test_import_all_modules(self):
        """Walk package and import everything."""
        package = wildcards_gen
        prefix = package.__name__ + "."

        for _, name, is_pkg in pkgutil.walk_packages(package.__path__, prefix):
            try:
                importlib.import_module(name)
            except Exception as e:
                self.fail(f"Failed to import module {name}: {e}")

if __name__ == '__main__':
    unittest.main()
