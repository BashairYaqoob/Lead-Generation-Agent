"""Browser automation module (stub).

This module will contain Playwright-based automation logic for navigating
map/business listing websites (e.g. Google Maps, Bing Maps) to search for
and open businesses.

Not implemented yet. This is a placeholder to establish the module boundary
for the next development stage.
"""

from models import SearchQuery


class BrowserAutomation:
    """Handles browser automation for searching business listings.

    This class will eventually wrap a Playwright browser session to perform
    searches on a map/business listing website and yield business result
    handles for scraping.
    """

    def __init__(self, headless: bool = True) -> None:
        """Initialize the browser automation handler.

        Args:
            headless: Whether the browser should run in headless mode.
        """
        self.headless = headless

    def launch(self) -> None:
        """Launch the browser session.

        Raises:
            NotImplementedError: Browser automation is not yet implemented.
        """
        raise NotImplementedError("Browser automation will be implemented in a later stage.")

    def search(self, query: SearchQuery) -> None:
        """Search for businesses matching the given query.

        Args:
            query: The parsed search query (business type + location).

        Raises:
            NotImplementedError: Browser automation is not yet implemented.
        """
        raise NotImplementedError("Browser automation will be implemented in a later stage.")

    def close(self) -> None:
        """Close the browser session.

        Raises:
            NotImplementedError: Browser automation is not yet implemented.
        """
        raise NotImplementedError("Browser automation will be implemented in a later stage.")