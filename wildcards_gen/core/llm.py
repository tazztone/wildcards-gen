"""
LLM Engine for AI-powered taxonomy generation.

Handles communication with OpenRouter API for:
- Structure generation
- Term categorization  
- Instruction enrichment

Ported from wildcards-categorize.
"""

import requests
import json
import logging
import os
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class LLMEngine:
    """Handles LLM API calls for taxonomy generation."""

    def __init__(
        self,
        api_key: str,
        model: str = "openai/gpt-4o-mini",
        base_url: str = "https://openrouter.ai/api/v1"
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.prompts_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "prompts"
        )

    def _load_prompt(self, filename: str) -> str:
        """Load a prompt template from file."""
        try:
            path = os.path.join(self.prompts_dir, filename)
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.error(f"Prompt file {filename} not found at {path}")
            return ""
    def _clean_response(self, text: str) -> str:
        """Strip markdown code blocks from response."""
        if not text:
            return ""
        cleaned = text.strip()
        
        # Remove opening fence
        if cleaned.startswith("```"):
            # Find first newline to skip language identifier
            first_newline = cleaned.find("\n")
            if first_newline != -1:
                cleaned = cleaned[first_newline+1:].strip()
            else:
                # Startswith ``` but no newline? Just strip 3 chars
                cleaned = cleaned[3:].strip()
        
        # Remove closing fence
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()
            
        return cleaned

    def _call_api(
        self,
        messages: List[Dict[str, str]],
        response_format: Optional[Dict] = None,
        timeout: int = 120
    ) -> Optional[str]:
        """Make an API call to the LLM provider."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/tazztone/wildcards-gen",
        }

        data = {
            "model": self.model,
            "messages": messages,
        }
        if response_format:
            data["response_format"] = response_format

        try:
            logger.info(f"Calling {self.base_url} with model {self.model}")
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=timeout
            )
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']

        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            return None

    def generate_structure(
        self,
        sample_terms: List[str],
        current_structure_yaml: str = ""
    ) -> Optional[str]:
        """
        Generate a taxonomy structure from sample terms.
        
        Returns YAML string with categories and # instruction: comments.
        """
        prompt_template = self._load_prompt("generate_structure.txt")
        if not prompt_template:
            return None

        prompt = prompt_template.format(
            count=len(sample_terms),
            sample_terms=", ".join(sample_terms[:50]),  # Limit sample size
            current_structure=current_structure_yaml or "(empty)"
        )

        messages = [{"role": "user", "content": prompt}]
        return self._call_api(messages)

    def categorize_terms(
        self,
        terms: List[str],
        structure_yaml: str
    ) -> Optional[Dict[str, Any]]:
        """
        Categorize terms into an existing structure.
        
        Returns a dict representing the categorized terms.
        """
        prompt_template = self._load_prompt("categorize_terms.txt")
        if not prompt_template:
            return None

        prompt = prompt_template.format(
            structure_with_instructions=structure_yaml,
            terms=", ".join(terms)
        )

        messages = [{"role": "user", "content": prompt}]
        response_text = self._call_api(
            messages,
            response_format={"type": "json_object"}
        )

        if not response_text:
            return None

        try:
            cleaned = self._clean_response(response_text)
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            logger.error(f"Response: {response_text}")
            return None

    def enrich_instructions(
        self,
        structure_yaml: str,
        topic: str = "AI image generation wildcards"
    ) -> Optional[str]:
        """
        Add or improve # instruction: comments in an existing structure.
        
        Returns enhanced YAML string.
        """
        prompt = f"""You are an expert at creating helpful descriptions for taxonomy categories.

Given this YAML structure for {topic}:

{structure_yaml}

For each category that lacks a good `# instruction:` comment, add one.
The instruction should clearly explain what types of items belong in that category.

Keep existing good instructions. Improve vague or missing ones.

Output ONLY valid YAML with the instructions as end-of-line comments in the format:
CategoryName: # instruction: description here
"""
        messages = [{"role": "user", "content": prompt}]
        return self._call_api(messages)

    def generate_dynamic_structure(
        self,
        topic: str = "AI Image Generation"
    ) -> Optional[str]:
        """
        Generate a complete taxonomy structure for a topic from scratch.
        Uses multi-phase approach: roots → validation → tree building.
        """
        # Phase 0: Generate root categories
        roots_prompt = self._load_prompt("phase0_meta_architect.txt")
        if not roots_prompt:
            return None

        prompt = roots_prompt.format(topic=topic)
        response = self._call_api([{"role": "user", "content": prompt}])
        roots = self._clean_response(response) if response else None
        
        if not roots:
            logger.error("Phase 0 failed: Could not generate roots")
            return None
        logger.info(f"Generated roots: {roots[:200]}...")

        # Phase 1: Build taxonomy from roots
        mason_prompt = self._load_prompt("phase1_mason.txt")
        if not mason_prompt:
            return None

        prompt = mason_prompt.format(roots=roots)
        response = self._call_api([{"role": "user", "content": prompt}])
        structure = self._clean_response(response) if response else None
        
        if not structure:
            logger.error("Phase 1 failed: Could not build tree")
            return None

        return structure
