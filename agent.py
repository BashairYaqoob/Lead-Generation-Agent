"""Core orchestration logic for the Lead Generation Agent.

Coordinates prompt parsing, browser automation, scraping (including email
discovery), and Excel export to produce a complete lead-generation run for
a given natural language prompt.
"""

from dataclasses import dataclass

import config
from browser import BrowserAgent
from excel_export import ExcelExporter
from models import Lead, SearchQuery
from parser import PromptParser
from scraper import BusinessScraper
from utils import configure_logging, sanitize_filename

logger = configure_logging()


@dataclass
class RunResult:
    """Summarizes the outcome of a full agent run.

    Attributes:
        query: The parsed search query.
        leads: All successfully collected leads.
        emails_found: Count of leads with a non-empty email address.
        excel_path: Path to the saved Excel file, or None if export was
            skipped (e.g. because no leads were collected).
    """

    query: SearchQuery
    leads: list[Lead]
    emails_found: int
    excel_path: str | None


class LeadGenerationAgent:
    """Orchestrates the end-to-end lead generation workflow.

    Workflow:
        User Prompt -> PromptParser -> SearchQuery
                    -> BrowserAgent (search + collect + open results)
                    -> BusinessScraper (extract details + email)
                    -> list[Lead]
                    -> ExcelExporter -> RunResult (summary)
    """

    def __init__(self) -> None:
        """Initialize the agent's parser, scraper, and exporter."""
        self.parser = PromptParser()
        self.scraper = BusinessScraper()
        self.exporter = ExcelExporter()

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
        """Open a single business result and scrape its details (incl. email).

        Any failure while opening or scraping a single result is logged
        and treated as a skipped result; it never stops the overall run.

        Args:
            browser: An already-launched BrowserAgent with active results.
            index: Zero-based index of the result to open.
            location: Fallback location used if no address is found.

        Returns:
            A populated Lead, or None if the result could not be opened
            or scraped.
        """
        try:
            opened = browser.open_result(index)
            if not opened:
                logger.warning("Could not open business result at index %d.", index)
                return None
            return self.scraper.scrape(browser.page, location)
        except Exception as exc:  # noqa: BLE001 - never let one bad result stop the run
            logger.warning("Failed to scrape business at index %d: %s", index, exc)
            return None

    def save_to_excel(self, leads: list[Lead], filename: str) -> str | None:
        """Save collected leads to an Excel file.

        Args:
            leads: The list of collected Lead objects.
            filename: The desired output filename.

        Returns:
            The full path to the saved file, or None if saving failed.
        """
        try:
            return self.exporter.export(leads, filename)
        except OSError as exc:
            logger.error("Failed to save Excel file: %s", exc)
            return None

    def run(self, prompt: str) -> RunResult:
        """Run the full parse -> search -> scrape -> export workflow.

        Args:
            prompt: The raw natural language prompt from the user.

        Returns:
            A RunResult summarizing the query, collected leads, email
            discovery count, and the saved Excel file path.

        Raises:
            ValueError: If the prompt cannot be parsed.
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
        except (TimeoutError, RuntimeError) as exc:
            logger.error("Browser automation failed: %s", exc)
        finally:
            browser.close()

        emails_found = sum(1 for lead in leads if lead.email)

        excel_path: str | None = None
        if leads:
            filename = f"leads_{sanitize_filename(query.business_type)}"
            excel_path = self.save_to_excel(leads, filename)

        return RunResult(
            query=query,
            leads=leads,
            emails_found=emails_found,
            excel_path=excel_path,
        )