"""Browser automation for searching business listings on Google Maps.

This module wraps the Playwright Sync API to launch a Chromium browser,
perform a search on Google Maps, progressively scroll the results panel to
load multiple businesses, and open individual business listings so that
`scraper.py` can extract their details from the resulting detail pane.

Selectors are centralized as module-level constants since Google Maps'
markup changes periodically; if scraping breaks, these are the first
things to update.
"""

from playwright.sync_api import (
    Browser,
    Error as PlaywrightError,
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)

GOOGLE_MAPS_URL = "https://www.google.com/maps"

# Search UI selectors.
SEARCH_INPUT_SELECTOR = "input#searchboxinput"
SEARCH_BUTTON_SELECTOR = "button#searchbox-searchbutton"

# Results panel selectors.
RESULTS_FEED_SELECTOR = 'div[role="feed"]'
RESULT_ITEM_SELECTOR = 'div[role="feed"] a.hfpxzc'

# Selector used to confirm a business detail pane has loaded after a click.
BUSINESS_NAME_SELECTOR = "h1.DUwDvf"

# Maximum number of consecutive scroll attempts that yield no new results
# before we conclude no more businesses are available.
_MAX_STAGNANT_SCROLLS = 3

# Brief wait after each scroll to allow lazy-loaded results to render.
_SCROLL_WAIT_MS = 1000


class BrowserAgent:
    """Manages a Playwright Chromium session for Google Maps automation.

    Typical usage:
        agent = BrowserAgent(headless=True, search_timeout=15000)
        agent.launch()
        agent.search("coffee shops Karachi")
        count = agent.collect_businesses(max_results=20)
        for i in range(count):
            if agent.open_result(i):
                ...  # hand agent.page to BusinessScraper
        agent.close()
    """

    def __init__(self, headless: bool = True, search_timeout: int = 15000) -> None:
        """Initialize the browser agent.

        Args:
            headless: Whether Chromium should run without a visible window.
            search_timeout: Default timeout (milliseconds) for page waits
                and actions.
        """
        self.headless = headless
        self.search_timeout = search_timeout

        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self.page: Page | None = None

    def launch(self) -> None:
        """Launch Chromium and open a new page.

        Raises:
            RuntimeError: If the browser fails to launch.
        """
        try:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=self.headless)
            context = self._browser.new_context()
            self.page = context.new_page()
            self.page.set_default_timeout(self.search_timeout)
        except PlaywrightError as exc:
            self.close()
            raise RuntimeError(f"Failed to launch browser: {exc}") from exc

    def search(self, search_query: str) -> None:
        """Navigate to Google Maps and perform a search.

        Args:
            search_query: The full search string, e.g. "coffee shops Karachi".

        Raises:
            RuntimeError: If the browser has not been launched.
            TimeoutError: If the search UI or results feed never appear.
        """
        if self.page is None:
            raise RuntimeError("Browser has not been launched. Call launch() first.")

        try:
            self.page.goto(GOOGLE_MAPS_URL, timeout=self.search_timeout)
            self.page.wait_for_selector(SEARCH_INPUT_SELECTOR, timeout=self.search_timeout)
            self.page.fill(SEARCH_INPUT_SELECTOR, search_query)
            self.page.click(SEARCH_BUTTON_SELECTOR)
            self.page.wait_for_selector(RESULTS_FEED_SELECTOR, timeout=self.search_timeout)
        except PlaywrightTimeoutError as exc:
            raise TimeoutError(
                f"Timed out while searching Google Maps for '{search_query}': {exc}"
            ) from exc

    def collect_businesses(self, max_results: int) -> int:
        """Scroll the results panel to load multiple business listings.

        Args:
            max_results: The maximum number of businesses to load.

        Returns:
            The number of business result items currently available
            (capped at max_results).

        Raises:
            RuntimeError: If the browser has not been launched.
        """
        if self.page is None:
            raise RuntimeError("Browser has not been launched. Call launch() first.")

        if max_results <= 0:
            return 0

        results_locator = self.page.locator(RESULT_ITEM_SELECTOR)
        previous_count = 0
        stagnant_rounds = 0

        while stagnant_rounds < _MAX_STAGNANT_SCROLLS:
            current_count = results_locator.count()

            if current_count >= max_results:
                break

            if current_count == previous_count:
                stagnant_rounds += 1
            else:
                stagnant_rounds = 0

            previous_count = current_count

            try:
                self.page.locator(RESULTS_FEED_SELECTOR).evaluate(
                    "el => el.scrollTop = el.scrollHeight"
                )
            except PlaywrightError:
                # Feed may not be scrollable (e.g. too few results); stop trying.
                break

            self.page.wait_for_timeout(_SCROLL_WAIT_MS)

        final_count = results_locator.count()
        return min(final_count, max_results)

    def open_result(self, index: int) -> bool:
        """Open a business result by index and wait for its detail pane.

        Args:
            index: Zero-based index of the result item to open.

        Returns:
            True if the business detail pane loaded successfully, False
            if the click or load timed out.

        Raises:
            RuntimeError: If the browser has not been launched.
        """
        if self.page is None:
            raise RuntimeError("Browser has not been launched. Call launch() first.")

        try:
            self.page.locator(RESULT_ITEM_SELECTOR).nth(index).click(
                timeout=self.search_timeout
            )
            self.page.wait_for_selector(BUSINESS_NAME_SELECTOR, timeout=self.search_timeout)
            return True
        except (PlaywrightTimeoutError, PlaywrightError):
            return False

    def close(self) -> None:
        """Close the browser and clean up Playwright resources.

        Safe to call multiple times or after a failed launch.
        """
        if self._browser is not None:
            try:
                self._browser.close()
            except PlaywrightError:
                pass
            self._browser = None

        if self._playwright is not None:
            try:
                self._playwright.stop()
            except PlaywrightError:
                pass
            self._playwright = None

        self.page = None