"""Core orchestration logic for the Lead Generation Agent.

Currently only wires together prompt parsing. Business search, scraping,
and Excel export are stubbed out and will be implemented in later stages.
"""

from models import Lead, SearchQuery
from parser import PromptParser


class LeadGenerationAgent:
    """Orchestrates the end-to-end lead generation workflow.

    Workflow (current stage):
        User Prompt -> PromptParser -> SearchQuery -> printed result

    Workflow (future stages):
        SearchQuery -> BrowserAutomation -> BusinessScraper -> list[Lead]
                    -> ExcelExporter -> summary
    """

    def __init__(self) -> None:
        """Initialize the agent and its prompt parser."""
        self.parser = PromptParser()

    def parse_prompt(self, prompt: str) -> SearchQuery:
        """Parse a raw user prompt into a structured SearchQuery.

        Args:
            prompt: The raw natural language prompt from the user.

        Returns:
            The parsed SearchQuery.
        """
        return self.parser.parse(prompt)

    def search_businesses(self, query: SearchQuery) -> None:
        """Search for businesses matching the given query.

        Args:
            query: The parsed search query.

        Raises:
            NotImplementedError: Business search is not yet implemented.
        """
        raise NotImplementedError("search_businesses() will be implemented in a later stage.")

    def scrape_business(self, location: str) -> Lead:
        """Scrape a single business into a Lead object.

        Args:
            location: The location associated with the current search.

        Raises:
            NotImplementedError: Scraping is not yet implemented.
        """
        raise NotImplementedError("scrape_business() will be implemented in a later stage.")

    def save_to_excel(self, leads: list[Lead], filename: str) -> str:
        """Save collected leads to an Excel file.

        Args:
            leads: The list of collected Lead objects.
            filename: The desired output filename.

        Raises:
            NotImplementedError: Excel export is not yet implemented.
        """
        raise NotImplementedError("save_to_excel() will be implemented in a later stage.")

    def run(self, prompt: str) -> SearchQuery:
        """Run the current (partial) agent workflow for a given prompt.

        At this stage, the agent only parses the prompt and returns the
        resulting SearchQuery. Later stages will extend this method to
        perform the full search -> scrape -> export pipeline.

        Args:
            prompt: The raw natural language prompt from the user.

        Returns:
            The parsed SearchQuery.
        """
        query = self.parse_prompt(prompt)
        return query