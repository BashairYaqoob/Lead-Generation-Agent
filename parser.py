"""Prompt parsing utilities.

This module is responsible for converting a natural language search prompt
(e.g. "Find coffee shops in Karachi") into a structured SearchQuery object.

The current implementation is rule-based (regex + heuristics) and is
intentionally isolated behind the PromptParser class so it can be swapped
for an LLM-backed implementation later without changing any other module.
"""

import re

from models import SearchQuery

# Words that commonly precede the actual request and carry no semantic
# meaning for business type or location extraction.
_LEADING_FILLER_PATTERN = re.compile(
    r"^\s*(find|i need|i want|get me|search for|look for|show me)\s+",
    re.IGNORECASE,
)

# Captures "<business_type> in <location>", allowing "in" to appear
# anywhere in the trailing location clause (e.g. "in the city of Lahore").
_BUSINESS_LOCATION_PATTERN = re.compile(
    r"^(?P<business_type>.+?)\s+in\s+(?P<location>.+)$",
    re.IGNORECASE,
)


class PromptParser:
    """Parses natural language prompts into structured SearchQuery objects.

    This is a rule-based implementation using regular expressions and simple
    heuristics. It is designed to be a drop-in interface: a future
    LLM-backed parser can implement the same `parse` method signature.
    """

    def parse(self, prompt: str) -> SearchQuery:
        """Parse a natural language prompt into a SearchQuery.

        Args:
            prompt: The raw user prompt, e.g. "Find coffee shops in Karachi".

        Returns:
            A SearchQuery with the extracted business_type and location.

        Raises:
            ValueError: If the prompt is empty or no business/location
                pattern could be identified.
        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt must not be empty.")

        cleaned = self._strip_filler_words(prompt.strip())

        match = _BUSINESS_LOCATION_PATTERN.match(cleaned)
        if not match:
            raise ValueError(
                f"Could not parse business type and location from prompt: '{prompt}'. "
                "Expected a pattern like '<business type> in <location>'."
            )

        business_type = match.group("business_type").strip()
        location = match.group("location").strip()

        if not business_type or not location:
            raise ValueError(
                f"Could not extract both business type and location from prompt: '{prompt}'."
            )

        return SearchQuery(
            business_type=self._normalize_text(business_type),
            location=self._normalize_text(location),
        )

    @staticmethod
    def _strip_filler_words(text: str) -> str:
        """Remove common leading filler phrases (e.g. 'Find', 'I need').

        Args:
            text: The input text to clean.

        Returns:
            The text with leading filler phrases removed.
        """
        return _LEADING_FILLER_PATTERN.sub("", text)

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalize extracted text by trimming whitespace and punctuation.

        Args:
            text: The text to normalize.

        Returns:
            The normalized text.
        """
        return text.strip().strip(".,!?").strip()