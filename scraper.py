"""Business data scraping from Google Maps detail panes.

Given a Playwright Page that currently has a business detail pane open
(after `BrowserAgent.open_result()`), extracts the visible business name,
phone number, website, and address into a `Lead` object.

Email extraction is intentionally left as an empty string; it will be
implemented in a later stage by visiting each business's website.
"""

from playwright.sync_api import Error as PlaywrightError, Page, TimeoutError as PlaywrightTimeoutError

from models import Lead

NAME_SELECTOR = "h1.DUwDvf"
ADDRESS_SELECTOR = 'button[data-item-id="address"]'
PHONE_SELECTOR = 'button[data-item-id^="phone:tel:"]'
WEBSITE_SELECTOR = 'a[data-item-id="authority"]'

# Timeout (milliseconds) for individual field extraction attempts. Kept
# short since the detail pane is already loaded by the time we scrape it.
_FIELD_TIMEOUT_MS = 3000


class BusinessScraper:
    """Extracts structured lead data from an open Google Maps detail pane."""

    def scrape(self, page: Page, location: str) -> Lead:
        """Scrape the currently open business detail pane into a Lead.

        Any field that cannot be found is left as an empty string; this
        method never raises due to missing data.

        Args:
            page: The Playwright Page with a business detail pane open.
            location: Fallback location (from the search query) used if
                no address can be extracted from the page.

        Returns:
            A populated Lead object.
        """
        name = self._extract_text(page, NAME_SELECTOR)
        address = self._extract_attribute_or_text(page, ADDRESS_SELECTOR, "aria-label")
        phone = self._extract_attribute_or_text(page, PHONE_SELECTOR, "aria-label")
        website = self._extract_attribute(page, WEBSITE_SELECTOR, "href")

        return Lead(
            business_name=name,
            email="",
            phone_number=self._clean_aria_label(phone),
            website=website,
            location=self._clean_aria_label(address) or location,
        )

    @staticmethod
    def _extract_text(page: Page, selector: str) -> str:
        """Extract the text content of the first element matching selector.

        Args:
            page: The Playwright Page to search within.
            selector: The CSS selector to locate the element.

        Returns:
            The trimmed text content, or an empty string if not found.
        """
        try:
            locator = page.locator(selector).first
            text = locator.text_content(timeout=_FIELD_TIMEOUT_MS)
            return text.strip() if text else ""
        except (PlaywrightTimeoutError, PlaywrightError):
            return ""

    @staticmethod
    def _extract_attribute(page: Page, selector: str, attribute: str) -> str:
        """Extract an attribute value from the first element matching selector.

        Args:
            page: The Playwright Page to search within.
            selector: The CSS selector to locate the element.
            attribute: The name of the attribute to read.

        Returns:
            The attribute value, or an empty string if not found.
        """
        try:
            locator = page.locator(selector).first
            value = locator.get_attribute(attribute, timeout=_FIELD_TIMEOUT_MS)
            return value.strip() if value else ""
        except (PlaywrightTimeoutError, PlaywrightError):
            return ""

    def _extract_attribute_or_text(self, page: Page, selector: str, attribute: str) -> str:
        """Try extracting an attribute first, falling back to text content.

        Google Maps often stores the most descriptive value (e.g. the full
        address or phone number) inside an `aria-label` rather than the
        element's visible text.

        Args:
            page: The Playwright Page to search within.
            selector: The CSS selector to locate the element.
            attribute: The attribute to prefer.

        Returns:
            The extracted value, or an empty string if neither is found.
        """
        value = self._extract_attribute(page, selector, attribute)
        if value:
            return value
        return self._extract_text(page, selector)

    @staticmethod
    def _clean_aria_label(raw_value: str) -> str:
        """Strip common Google Maps aria-label prefixes (e.g. 'Address: ').

        Args:
            raw_value: The raw aria-label or text value.

        Returns:
            The cleaned value with any known prefix removed.
        """
        if not raw_value:
            return ""

        for prefix in ("Address: ", "Phone: "):
            if raw_value.startswith(prefix):
                return raw_value[len(prefix):].strip()

        return raw_value.strip()