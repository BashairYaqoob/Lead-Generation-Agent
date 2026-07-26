"""Browser automation for searching business listings on Google Maps.

This module wraps the Playwright Sync API to launch a Chromium browser,
perform a search on Google Maps, progressively scroll the results panel to
load multiple businesses, and open individual business listings so that
`scraper.py` can extract their details from the resulting detail pane.

`launch()` applies a realistic user agent and a light init script that
masks `navigator.webdriver`, since Google Maps can behave differently for
obviously-automated browsers. These are best-effort; if Maps still
misbehaves, consider switching the target site (see README).

Selectors are centralized as module-level constants since Google Maps'
markup changes periodically; if scraping breaks, these are the first
things to update.
"""

import os

from playwright.sync_api import (
    Browser,
    Error as PlaywrightError,
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)

GOOGLE_MAPS_URL = "https://www.google.com/maps"

# A realistic, current desktop Chrome user agent. Using Playwright's default
# "HeadlessChrome"/automation-flavored UA makes bot detection trivial.
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# NOTE: We intentionally do NOT pass "--start-maximized" here. Combining it
# with an explicit context viewport causes Chromium to size the page
# inconsistently, which can leave interactive elements (like the search
# box) unstable or delayed. We rely on the explicit viewport below instead.
_LAUNCH_ARGS = [
    "--disable-blink-features=AutomationControlled",
]

# Runs before any page script, masking the most obvious automation signal.
_STEALTH_INIT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
window.chrome = window.chrome || { runtime: {} };
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
"""

# Search UI selectors.
SEARCH_INPUT_SELECTOR = 'input[role="combobox"]'
SEARCH_BUTTON_SELECTOR = 'button#searchbox-searchbutton'

# Results panel selectors.
RESULTS_FEED_SELECTOR = 'div[role="feed"]'
RESULT_ITEM_SELECTOR = (
    'div[role="feed"] a[href*="maps"]'
)

# Selector used to confirm a business detail pane has loaded after a click.
BUSINESS_NAME_SELECTOR = "h1.DUwDvf"

# Google's cookie consent screen (consent.google.com) sometimes intercepts
# the initial navigation on a fresh browser profile, before the Maps UI
# loads. These selectors cover the common consent button labels/locales.
_CONSENT_BUTTON_SELECTORS = [
    'button:has-text("Accept all")',
    'button:has-text("I agree")',
    'button:has-text("Reject all")',
    'form[action*="consent"] button',
]

# Short timeout used only to *check* whether a consent dialog is present.
_CONSENT_CHECK_TIMEOUT_MS = 2500

# Maximum number of consecutive scroll attempts that yield no new results
# before we conclude no more businesses are available.
_MAX_STAGNANT_SCROLLS = 3

# Brief wait after each scroll to allow lazy-loaded results to render.
_SCROLL_WAIT_MS = 1000

# Directory where a diagnostic screenshot is saved if a search times out,
# to make debugging selector/loading issues easier without guesswork.
_DEBUG_DIR = "output/debug"


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
        """Launch Chromium and open a new page with anti-detection tweaks.

        Raises:
            RuntimeError: If the browser fails to launch.
        """
        try:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(
                headless=self.headless,
                args=_LAUNCH_ARGS,
            )
            context = self._browser.new_context(
                locale="en-US",
                user_agent=_USER_AGENT,
                viewport={"width": 1366, "height": 850},
                extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
            )
            context.add_init_script(_STEALTH_INIT_SCRIPT)
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
            RuntimeError: If the browser has not been launched, or if the
                page/context/browser closed unexpectedly.
            TimeoutError: If the search UI or results feed never appear
                within the configured timeout.
        """
        if self.page is None:
            raise RuntimeError("Browser has not been launched. Call launch() first.")

        try:
            self.page.goto(GOOGLE_MAPS_URL, timeout=self.search_timeout, wait_until="domcontentloaded")
            self._dismiss_consent_dialog()
            self.page.wait_for_selector(SEARCH_INPUT_SELECTOR, timeout=self.search_timeout)
            self.search_box = self.page.locator('input[role="combobox"]').first
            self.search_box.wait_for(state="visible")
            self.search_box.fill(search_query)
            self.search_box.press("Enter")
            self.page.wait_for_selector(RESULTS_FEED_SELECTOR, timeout=self.search_timeout)
        except PlaywrightTimeoutError as exc:
            self._save_debug_screenshot("search_timeout")
            raise TimeoutError(
                f"Timed out while searching Google Maps for '{search_query}': {exc}"
            ) from exc
        except PlaywrightError as exc:
            if "closed" in str(exc).lower():
                raise RuntimeError(
                    "The browser session closed unexpectedly while searching Google Maps."
                ) from exc
            raise RuntimeError(f"Browser error while searching Google Maps: {exc}") from exc

    def _dismiss_consent_dialog(self) -> None:
        """Dismiss Google's cookie consent dialog if it appears.

        Checks briefly for common consent buttons and clicks the first one
        found. If no dialog appears, does nothing. Never raises.
        """
        if self.page is None:
            return

        for selector in _CONSENT_BUTTON_SELECTORS:
            try:
                button = self.page.locator(selector).first
                button.wait_for(state="visible", timeout=_CONSENT_CHECK_TIMEOUT_MS)
                button.click(timeout=_CONSENT_CHECK_TIMEOUT_MS)
                self.page.wait_for_load_state("domcontentloaded", timeout=self.search_timeout)
                return
            except (PlaywrightTimeoutError, PlaywrightError):
                continue

    def _save_debug_screenshot(self, label: str) -> None:
        """Save a screenshot of the current page state, for debugging.

        Never raises: any failure while saving is silently ignored, since
        this is a best-effort diagnostic aid, not a core feature.

        Args:
            label: A short label used in the screenshot filename.
        """
        if self.page is None:
            return

        try:
            os.makedirs(_DEBUG_DIR, exist_ok=True)
            path = os.path.join(_DEBUG_DIR, f"{label}.png")
            self.page.screenshot(path=path)
            print(f"[debug] Saved screenshot to {path} (current URL: {self.page.url})")
        except PlaywrightError:
            pass

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

        # results_locator = self.page.locator(RESULT_ITEM_SELECTOR)
        previous_count = 0
        stagnant_rounds = 0

        while stagnant_rounds < _MAX_STAGNANT_SCROLLS:
            results_locator = self.page.locator(RESULT_ITEM_SELECTOR)
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
                break

            self.page.wait_for_timeout(_SCROLL_WAIT_MS)

        final_count = results_locator.count()
        return min(final_count, max_results)

    def open_result(self, index: int) -> bool:
        if self.page is None:
            raise RuntimeError("Browser has not been launched.")

        previous_name = self._current_business_name()

        for attempt in range(3):
            try:
                results = self.page.locator(RESULT_ITEM_SELECTOR)

                if index >= results.count():
                    return False

                result = results.nth(index)

                result.scroll_into_view_if_needed()

                result.wait_for(
                    state="visible",
                    timeout=5000,
                )

                result.click(
                    timeout=5000,
                    force=True,
                )
            # Wait for the SAME element's text to actually differ from
            # what it was before the click — wait_for_selector alone
            # resolves instantly if the element already exists from the
            # previously opened business, causing a stale read.

                self.page.wait_for_function(
                    """([selector, previous]) => {
                        const el = document.querySelector(selector);
                        const text = el && el.textContent.trim();
                        return !!text && text !== previous;
                    }""",
                    arg=[BUSINESS_NAME_SELECTOR, previous_name],
                    timeout=self.search_timeout,
                )

                return True

            except (PlaywrightTimeoutError, PlaywrightError):

                self.page.wait_for_timeout(1000)

        return False

    def _current_business_name(self) -> str:
        """Snapshot the currently displayed business name, if any (empty before the first open)."""
        if self.page is None:
            return ""
        try:
            text = self.page.locator(BUSINESS_NAME_SELECTOR).first.text_content(timeout=1000)
            return text.strip() if text else ""
        except (PlaywrightTimeoutError, PlaywrightError):
            return ""

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