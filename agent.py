"""Core orchestration logic for the Lead Generation Agent.

Coordinates prompt parsing, browser automation, scraping (including email
discovery), and Excel export. Tracks detailed run statistics (successful
vs. skipped businesses, field discovery counts, execution time) and prints
step-by-step progress so failures are easy to diagnose without stopping
the overall run.
"""

import time
from dataclasses import dataclass, field

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
        businesses_processed: Total number of business results attempted.
        successful: Number of businesses successfully opened and scraped.
        skipped: Number of businesses that could not be opened after retries.
        emails_found: Count of leads with a non-empty email address.
        phones_found: Count of leads with a non-empty phone number.
        websites_found: Count of leads with a non-empty website.
        excel_path: Path to the saved Excel file, or None if not saved.
        execution_time_seconds: Total wall-clock time for the run.
    """

    query: SearchQuery
    leads: list[Lead] = field(default_factory=list)
    businesses_processed: int = 0
    successful: int = 0
    skipped: int = 0
    emails_found: int = 0
    phones_found: int = 0
    websites_found: int = 0
    excel_path: str | None = None
    execution_time_seconds: float = 0.0


class LeadGenerationAgent:
    """Orchestrates the end-to-end lead generation workflow."""

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
        logger.info("Searching Google Maps...")
        search_text = f"{query.business_type} {query.location}"
        browser.search(search_text)

        logger.info("Loading businesses...")
        return browser.collect_businesses(max_results=config.MAX_LEADS)

    def scrape_business(self, browser: BrowserAgent, index: int, location: str) -> Lead | None:
        """Open a single business result and scrape its details (incl. email).

        Any failure is logged and treated as a skipped result; it never
        stops the overall run.

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
            A RunResult summarizing the query, collected leads, and stats.

        Raises:
            ValueError: If the prompt cannot be parsed.
        """
        start_time = time.perf_counter()
        query = self.parse_prompt(prompt)

        result = RunResult(query=query)
        browser = BrowserAgent(headless=config.HEADLESS, search_timeout=config.SEARCH_TIMEOUT)

        try:
            logger.info("Launching browser...")
            browser.launch()

            result_count = self.search_businesses(browser, query)
            result.businesses_processed = result_count

            for index in range(result_count):
                logger.info("Business %d/%d", index + 1, result_count)
                lead = self.scrape_business(browser, index, query.location)

                if lead is None:
                    result.skipped += 1
                    logger.warning("\u2717 Skipped\n" + "-" * 23)
                    continue

                result.leads.append(lead)
                result.successful += 1
                if lead.email:
                    result.emails_found += 1
                if lead.phone_number:
                    result.phones_found += 1
                if lead.website:
                    result.websites_found += 1
                logger.info("\u2713 Success\n" + "-" * 23)

        except (TimeoutError, RuntimeError) as exc:
            logger.error("Browser automation failed: %s", exc)
        finally:
            browser.close()

        if result.leads:
            filename = f"leads_{sanitize_filename(query.business_type)}"
            result.excel_path = self.save_to_excel(result.leads, filename)

        result.execution_time_seconds = round(time.perf_counter() - start_time, 1)
        return result