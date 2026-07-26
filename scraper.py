"""Business data scraping from Google Maps detail panes, plus email discovery.

Given a Playwright Page that currently has a business detail pane open
(after `BrowserAgent.open_result()`), extracts the visible business name,
phone number, website, and address into a `Lead`.

Additionally, if a website URL is available, visits the homepage and a
small set of likely contact/about pages (via plain HTTP requests, not
Playwright) to search for a contact email address using a regular
expression. Any failure (unreachable site, timeout, malformed HTML) is
handled gracefully and simply results in an empty email field.
"""

import re
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import Error as PlaywrightError, Page, TimeoutError as PlaywrightTimeoutError

import config
from models import Lead

NAME_SELECTOR = "h1.DUwDvf"
ADDRESS_SELECTOR = 'button[data-item-id="address"]'
PHONE_SELECTOR = 'button[data-item-id^="phone:tel:"]'
WEBSITE_SELECTOR = 'a[data-item-id="authority"]'

# Timeout (milliseconds) for individual field extraction attempts. Kept
# short since the detail pane is already loaded by the time we scrape it.
_FIELD_TIMEOUT_MS = 3000

# Relative paths commonly used for contact/about information.
_CANDIDATE_PATHS = ["", "contact", "contact-us", "about", "about-us"]

# Keywords used to identify contact/about links discovered on a homepage.
_CONTACT_LINK_KEYWORDS = ("contact", "about")

# Matches standard email addresses (e.g. info@example.com).
_EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

# A stricter pattern used to validate a single candidate string.
_EMAIL_FULLMATCH_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

_REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; LeadGenerationAgent/1.0; "
        "+https://example.com/bot)"
    )
}


class BusinessScraper:
    """Extracts structured lead data from an open Google Maps detail pane."""

    def scrape(self, page: Page, location: str) -> Lead:
        """Scrape the currently open business detail pane into a Lead.

        Any field that cannot be found is left as an empty string; this
        method never raises due to missing data. If a website is found,
        it is also used to attempt email discovery.

        Args:
            page: The Playwright Page with a business detail pane open.
            location: Fallback location (from the search query) used if
                no address is extracted from the page.

        Returns:
            A populated Lead object.
        """
        name = self._extract_text(page, NAME_SELECTOR)
        address = self._extract_attribute_or_text(page, ADDRESS_SELECTOR, "aria-label")
        phone = self._extract_attribute_or_text(page, PHONE_SELECTOR, "aria-label")
        website = self._extract_attribute(page, WEBSITE_SELECTOR, "href")

        email = self.extract_email(website) if website else ""

        return Lead(
            business_name=name,
            email=email,
            phone_number=self._clean_aria_label(phone),
            website=website,
            location=self._clean_aria_label(address) or location,
        )

    # ------------------------------------------------------------------
    # Google Maps field extraction (Playwright)
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Email discovery (plain HTTP requests, independent of Playwright)
    # ------------------------------------------------------------------

    def extract_email(self, website: str) -> str:
        """Attempt to find a contact email address for a business website.

        Visits the homepage first; if no email is found, follows a small,
        bounded set of likely contact/about pages (discovered from the
        homepage's links, plus common path guesses) until an email is
        found or the page limit is reached.

        This method never raises: any network error, timeout, or parsing
        issue simply results in an empty string being returned.

        Args:
            website: The business website URL (may be empty).

        Returns:
            The first valid email address found, or an empty string.
        """
        if not website:
            return ""

        normalized_url = self._normalize_url(website)
        if not normalized_url:
            return ""

        homepage_html = self._fetch_page(normalized_url)
        if homepage_html:
            email = self.scan_page_for_email(homepage_html)
            if email:
                return email

        for contact_url in self.find_contact_page(normalized_url, homepage_html):
            html = self._fetch_page(contact_url)
            if not html:
                continue
            email = self.scan_page_for_email(html)
            if email:
                return email

        return ""

    def find_contact_page(self, base_url: str, homepage_html: str) -> list[str]:
        """Build a bounded list of candidate contact/about page URLs.

        Combines links discovered on the homepage (whose href or link text
        mentions "contact" or "about") with a fixed set of common path
        guesses (e.g. "/contact", "/about-us"), deduplicated and capped by
        `config.MAX_CONTACT_PAGES`.

        Args:
            base_url: The normalized website URL used to resolve relative links.
            homepage_html: The homepage HTML (may be empty if the homepage
                could not be fetched).

        Returns:
            A list of absolute candidate URLs to check for an email address.
        """
        candidates: list[str] = []

        discovered_links = self._discover_contact_links(base_url, homepage_html)
        candidates.extend(discovered_links)

        for path in _CANDIDATE_PATHS:
            if not path:
                continue
            candidates.append(urljoin(base_url + "/", path))

        deduped: list[str] = []
        seen: set[str] = set()
        for url in candidates:
            if url not in seen and url != base_url:
                seen.add(url)
                deduped.append(url)

        return deduped[: config.MAX_CONTACT_PAGES]

    def scan_page_for_email(self, html: str) -> str:
        """Search page HTML for the first valid email address.

        Args:
            html: The raw HTML content to search.

        Returns:
            The first valid email address found, or an empty string.
        """
        if not html:
            return ""

        try:
            soup = BeautifulSoup(html, "html.parser")
            text_content = soup.get_text(separator=" ")
        except Exception:
            text_content = html

        candidates = _EMAIL_PATTERN.findall(text_content)

        for candidate in candidates:
            cleaned = candidate.strip().rstrip(".,;:")
            if self.validate_email(cleaned):
                return cleaned

        return ""

    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate that a string is a well-formed email address.

        Args:
            email: The candidate email string.

        Returns:
            True if the string matches a standard email pattern.
        """
        if not email:
            return False
        return bool(_EMAIL_FULLMATCH_PATTERN.match(email))

    def _discover_contact_links(self, base_url: str, homepage_html: str) -> list[str]:
        """Find homepage links whose href or text suggests a contact/about page.

        Args:
            base_url: The base URL used to resolve relative links.
            homepage_html: The homepage HTML to search (may be empty).

        Returns:
            A list of absolute URLs discovered on the homepage.
        """
        if not homepage_html:
            return []

        try:
            soup = BeautifulSoup(homepage_html, "html.parser")
        except Exception:
            return []

        discovered: list[str] = []

        for anchor in soup.find_all("a", href=True):
            href = anchor.get("href", "")
            link_text = anchor.get_text(separator=" ").strip().lower()
            haystack = f"{href.lower()} {link_text}"

            if any(keyword in haystack for keyword in _CONTACT_LINK_KEYWORDS):
                absolute_url = urljoin(base_url, href)
                if self._is_same_domain(base_url, absolute_url):
                    discovered.append(absolute_url)

        return discovered

    @staticmethod
    def _is_same_domain(base_url: str, candidate_url: str) -> bool:
        """Check whether a candidate URL belongs to the same domain as base_url.

        Avoids following contact links that lead to unrelated third-party
        domains (e.g. social media widgets).

        Args:
            base_url: The reference website URL.
            candidate_url: The URL to check.

        Returns:
            True if both URLs share the same network location.
        """
        try:
            return urlparse(base_url).netloc == urlparse(candidate_url).netloc
        except ValueError:
            return False

    @staticmethod
    def _normalize_url(website: str) -> str:
        """Ensure a website URL has a scheme, defaulting to https://.

        Args:
            website: The raw website URL, possibly missing a scheme.

        Returns:
            A normalized absolute URL, or an empty string if invalid.
        """
        candidate = website.strip()
        if not candidate:
            return ""

        if not candidate.startswith(("http://", "https://")):
            candidate = f"https://{candidate}"

        try:
            parsed = urlparse(candidate)
            if not parsed.netloc:
                return ""
        except ValueError:
            return ""

        return candidate

    @staticmethod
    def _fetch_page(url: str) -> str:
        """Fetch a page's HTML content via a plain HTTP GET request.

        Any network error, timeout, or non-success status code results in
        an empty string rather than an exception.

        Args:
            url: The absolute URL to fetch.

        Returns:
            The response HTML, or an empty string on failure.
        """
        try:
            response = requests.get(
                url,
                headers=_REQUEST_HEADERS,
                timeout=config.EMAIL_TIMEOUT,
                allow_redirects=True,
            )
            if response.status_code >= 400:
                return ""
            return response.text
        except requests.exceptions.RequestException:
            return ""