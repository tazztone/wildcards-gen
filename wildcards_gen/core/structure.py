"""
Structure Manager for YAML with Comment Preservation

Uses ruamel.yaml to maintain # instruction: comments in the generated YAML.
Ported from wildcards-categorize.
"""

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from typing import Dict, Any, Optional, List
import io
import os
import logging

logger = logging.getLogger(__name__)


class StructureManager:
    """Manages YAML structure with comment preservation using ruamel.yaml."""

    def __init__(self):
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.indent(mapping=2, sequence=4, offset=2)
        self.yaml.width = 4096

    def create_empty_structure(self) -> CommentedMap:
        """Create an empty CommentedMap structure."""
        return CommentedMap()

    def add_category_with_instruction(
        self,
        parent_node: CommentedMap,
        key: str,
        instruction: Optional[str] = None
    ) -> None:
        """
        Add a category with an instruction comment to a parent node.
        
        Args:
            parent_node: The parent CommentedMap to add to
            key: Category name
            instruction: Optional instruction text (added as # instruction: comment)
        """
        if key not in parent_node:
            parent_node[key] = CommentedMap()

        if instruction:
            try:
                # Check if comment already exists
                if hasattr(parent_node, 'ca') and key in parent_node.ca.items:
                    pass  # Comment exists
                else:
                    parent_node.yaml_add_eol_comment(
                        f"instruction: {instruction}",
                        key
                    )
            except Exception as e:
                logger.warning(f"Failed to add comment for {key}: {e}")

    def add_leaf_list(
        self,
        parent_node: CommentedMap,
        key: str,
        items: List[str],
        instruction: Optional[str] = None
    ) -> None:
        """
        Add a leaf list (list of wildcard items) to a category.
        
        Args:
            parent_node: The parent CommentedMap
            key: Category name
            items: List of wildcard items
            instruction: Optional instruction for this category
        """
        seq = CommentedSeq(items)
        parent_node[key] = seq
        
        if instruction:
            try:
                parent_node.yaml_add_eol_comment(
                    f"instruction: {instruction}",
                    key
                )
            except Exception as e:
                logger.warning(f"Failed to add comment for {key}: {e}")

    def load_structure(self, file_path: str) -> CommentedMap:
        """Load YAML structure from file, preserving comments."""
        if not os.path.exists(file_path):
            return self.create_empty_structure()

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = self.yaml.load(f)
            return data if data is not None else self.create_empty_structure()
        except Exception as e:
            logger.error(f"Failed to load structure from {file_path}: {e}")
            return self.create_empty_structure()

    def save_structure(self, data: Any, file_path: str) -> None:
        """Save YAML structure to file, preserving comments."""
        content = self.to_string(data)

        try:
            os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Saved structure to {file_path}")
        except Exception as e:
            logger.error(f"Failed to save structure to {file_path}: {e}")

    def to_string(self, data: Any) -> str:
        """Convert structure to YAML string."""
        buf = io.StringIO()
        self.yaml.dump(data, buf)
        return buf.getvalue()

    def from_string(self, text: str) -> Any:
        """Parse YAML string to structure."""
        return self.yaml.load(text)

    def merge_categorized_data(
        self,
        current_structure: CommentedMap,
        categorized_data: Dict[str, Any]
    ) -> None:
        """
        Recursively merge categorized data into existing structure.
        Modifies current_structure in place.
        """
        for key, value in categorized_data.items():
            if isinstance(value, dict):
                if key not in current_structure:
                    current_structure[key] = self.create_empty_structure()

                if isinstance(current_structure[key], (dict, CommentedMap)):
                    self.merge_categorized_data(current_structure[key], value)
                else:
                    logger.warning(
                        f"Conflict at '{key}': existing is {type(current_structure[key])}, "
                        f"incoming is dict. Skipping."
                    )

            elif isinstance(value, list):
                if key not in current_structure:
                    current_structure[key] = CommentedSeq(value)
                elif isinstance(current_structure[key], (list, CommentedSeq)):
                    # Append unique terms
                    existing_set = set(current_structure[key])
                    for item in value:
                        if item not in existing_set:
                            current_structure[key].append(item)
                else:
                    logger.warning(
                        f"Conflict at '{key}': existing is {type(current_structure[key])}, "
                        f"incoming is list. Skipping."
                    )

    def extract_terms(self, data: Any) -> List[str]:
        """Extract all leaf terms from a structure."""
        found = []
        if isinstance(data, dict):
            for v in data.values():
                found.extend(self.extract_terms(v))
        elif isinstance(data, list):
            found.extend(data)
        return found
