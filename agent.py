"""Core orchestration logic for the Lead Generation Agent.

Coordinates prompt parsing, browser automation, and scraping to produce a
list of Lead objects for a given natural language prompt. Excel export is
still stubbed out and will be implemented in a later stage.
"""

import config
from browser import BrowserAgent
from models import Lead, SearchQuery
from parser import PromptParser
from scraper import BusinessScraper


class LeadGenerationAgent:
    """Orchestrates the end-to-end lead generation workflow.

    Workflow (current stage):
        User Prompt -> PromptParser -> SearchQuery
                    -> BrowserAgent (search + collect + open results)
                    -> BusinessScraper (extract details)
                    -> list[Lead]

    Workflow (future stage):
        list[Lead] -> ExcelExporter -> summary
    """

    def __init__(self) -> None:
        """Initialize the agent's parser and scraper."""
        self.parser = PromptParser()
        self.scraper = BusinessScraper()

    def parse_prompt(self, prompt: str) -> SearchQuery:
        """Parse a raw user prompt into a structured SearchQuery.

        Args:
            prompt: The raw natural language prompt from the user.

        Returns:
            The parsed SearchQuery.
        """
        return self.parser.parse(prompt)

    def search_businesses(self, browser: BrowserAgent, query: SearchQuery) -> int:
        """Search Google Maps and load multiple business results.

        Args:
            browser: An already-launched BrowserAgent.
            query: The parsed search query.

        Returns:
            The number of business results available to scrape.
        """
        search_text = f"{query.business_type} {query.location}"
        browser.search(search_text)
        return browser.collect_businesses(max_results=config.MAX_LEADS)

    def scrape_business(self, browser: BrowserAgent, index: int, location: str) -> Lead | None:
        """Open a single business result and scrape its details.

        Args:
            browser: An already-launched BrowserAgent with active results.
            index: Zero-based index of the result to open.
            location: Fallback location used if no address is found.

        Returns:
            A populated Lead, or None if the result could not be opened.
        """
        opened = browser.open_result(index)
        if not opened:
            return None
        return self.scraper.scrape(browser.page, location)

    def save_to_excel(self, leads: list[Lead], filename: str) -> str:
        """Save collected leads to an Excel file.

        Args:
            leads: The list of collected Lead objects.
            filename: The desired output filename.

        Raises:
            NotImplementedError: Excel export is not yet implemented.
        """
        raise NotImplementedError("save_to_excel() will be implemented in a later stage.")

    def run(self, prompt: str) -> list[Lead]:
        """Run the full search -> scrape workflow for a given prompt.

        Args:
            prompt: The raw natural language prompt from the user.

        Returns:
            A list of collected Lead objects (may be empty if no
            businesses were found or none could be opened).
        """
        query = self.parse_prompt(prompt)

        browser = BrowserAgent(headless=config.HEADLESS, search_timeout=config.SEARCH_TIMEOUT)
        leads: list[Lead] = []

        try:
            browser.launch()
            result_count = self.search_businesses(browser, query)

            for index in range(result_count):
                lead = self.scrape_business(browser, index, query.location)
                if lead is not None:
                    leads.append(lead)
        finally:
            browser.close()

        return leads