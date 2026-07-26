"""Business data scraping from Google Maps detail panes, plus email discovery.

Extracts business name, phone number, website, and address using
ARIA-label/role-based locators where possible (more stable across Google
Maps UI updates than generated CSS class names), falling back to
`data-item-id` attributes when needed. Also visits each business's website
(via plain HTTP requests, not Playwright) to search for a contact email
address, with retries for transient network failures.

Every extraction step degrades gracefully to an empty string on failure;
this module never raises due to missing or unreachable data.
"""

import re
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import Error as PlaywrightError, Page, TimeoutError as PlaywrightTimeoutError

import config
from models import Lead
from utils import configure_logging, retry

logger = configure_logging()

# --- Detail pane field locators ------------------------------------------
# Primary: aria-label based (accessible name), most stable.
# Fallback: data-item-id attribute (Google-internal but has been stable
# for years; used only if the aria-label lookup fails).
_ADDRESS_ARIA_PATTERN = re.compile(r"^Address:")
_PHONE_ARIA_PATTERN = re.compile(r"^Phone:")
_ADDRESS_FALLBACK_SELECTOR = 'button[data-item-id="address"]'
_PHONE_FALLBACK_SELECTOR = 'button[data-item-id^="phone:tel:"]'
# FRAGILE: "authority" is a Google-internal data-item-id used to mark the
# website link; there is no reliable aria-label alternative for this one.
_WEBSITE_SELECTOR = 'a[data-item-id="authority"]'

_FIELD_TIMEOUT_MS = 3000

_CANDIDATE_PATHS = ["", "contact", "contact-us", "about", "about-us"]
_CONTACT_LINK_KEYWORDS = ("contact", "about")

_EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
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

        Args:
            page: The Playwright Page with a business detail pane open.
            location: Fallback location used if no address is found.

        Returns:
            A populated Lead object. Missing fields are left as "".
        """
        name = self._extract_heading(page)
        address = self._extract_by_aria_or_fallback(
            page, _ADDRESS_ARIA_PATTERN, _ADDRESS_FALLBACK_SELECTOR
        )
        phone = self._extract_by_aria_or_fallback(
            page, _PHONE_ARIA_PATTERN, _PHONE_FALLBACK_SELECTOR
        )
        website = self._extract_attribute(page, _WEBSITE_SELECTOR, "href")

        logger.info("Extracting details...")
        if website:
            logger.info("Extracting website...")
            logger.info("Searching for email...")
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
    def _extract_heading(page: Page) -> str:
        print(page.url)
        try:
            headings = page.get_by_role("heading", level=1)

            for i in range(headings.count()):
                text = headings.nth(i).text_content(timeout=_FIELD_TIMEOUT_MS)

                if text and text.strip() and text.strip().lower() != "results":
                    return text.strip()

        except (PlaywrightTimeoutError, PlaywrightError):
            pass
        return ""

    @staticmethod
    def _extract_attribute(page: Page, selector: str, attribute: str) -> str:
        """Extract an attribute value from the first element matching selector.

        Args:
            page: The Playwright Page to search within.
            selector: The CSS selector to locate the element.
            attribute: The name of the attribute to read.

        Returns:
            The attribute value, or "" if not found.
        """
        try:
            locator = page.locator(selector).first
            value = locator.get_attribute(attribute, timeout=_FIELD_TIMEOUT_MS)
            return value.strip() if value else ""
        except (PlaywrightTimeoutError, PlaywrightError):
            return ""

    def _extract_by_aria_or_fallback(
        self, page: Page, aria_pattern: re.Pattern[str], fallback_selector: str
    ) -> str:
        """Extract a button's aria-label by accessible name, with a fallback.

        Tries a role-based lookup by accessible name pattern first (most
        stable); falls back to a `data-item-id` CSS selector if that fails.

        Args:
            page: The Playwright Page to search within.
            aria_pattern: Regex matching the expected accessible name prefix
                (e.g. "^Address:").
            fallback_selector: A `data-item-id`-based CSS selector to try
                if the role-based lookup finds nothing.

        Returns:
            The extracted aria-label text, or "" if neither approach works.
        """
        try:
            locator = page.get_by_role("button", name=aria_pattern).first
            value = locator.get_attribute("aria-label", timeout=_FIELD_TIMEOUT_MS)
            if value:
                return value.strip()
        except (PlaywrightTimeoutError, PlaywrightError):
            pass

        return self._extract_attribute(page, fallback_selector, "aria-label")

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

        Visits the homepage first, then a bounded set of likely
        contact/about pages, retrying each fetch on transient failures.
        Never raises: any unresolved failure results in "".

        Args:
            website: The business website URL (may be empty).

        Returns:
            The first valid email address found, or "".
        """
        if not website:
            return ""

        normalized_url = self._normalize_url(website)
        if not normalized_url:
            return ""

        homepage_html = self._fetch_page_with_retries(normalized_url)
        if homepage_html:
            email = self.scan_page_for_email(homepage_html)
            if email:
                return email

        for contact_url in self.find_contact_page(normalized_url, homepage_html):
            html = self._fetch_page_with_retries(contact_url)
            if not html:
                continue
            email = self.scan_page_for_email(html)
            if email:
                return email

        return ""

    def find_contact_page(self, base_url: str, homepage_html: str) -> list[str]:
        """Build a bounded list of candidate contact/about page URLs.

        Args:
            base_url: The normalized website URL used to resolve relative links.
            homepage_html: The homepage HTML (may be empty).

        Returns:
            A list of absolute candidate URLs, capped by config.MAX_CONTACT_PAGES.
        """
        candidates: list[str] = list(self._discover_contact_links(base_url, homepage_html))

        for path in _CANDIDATE_PATHS:
            if path:
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
            The first valid email address found, or "".
        """
        if not html:
            return ""

        try:
            soup = BeautifulSoup(html, "html.parser")
            text_content = soup.get_text(separator=" ")
        except Exception:
            text_content = html

        for candidate in _EMAIL_PATTERN.findall(text_content):
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
        return bool(email) and bool(_EMAIL_FULLMATCH_PATTERN.match(email))

    def _discover_contact_links(self, base_url: str, homepage_html: str) -> list[str]:
        """Find homepage links whose href or text suggests a contact/about page.

        Args:
            base_url: The base URL used to resolve relative links.
            homepage_html: The homepage HTML to search (may be empty).

        Returns:
            A list of same-domain absolute URLs discovered on the homepage.
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
            A normalized absolute URL, or "" if invalid.
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

    def _fetch_page_with_retries(self, url: str) -> str:
        """Fetch a page's HTML, retrying transient network failures.

        Args:
            url: The absolute URL to fetch.

        Returns:
            The response HTML, or "" if every attempt failed.
        """

        def attempt() -> str:
            return self._fetch_page(url)

        def on_retry(attempt_number: int, exc: BaseException) -> None:
            logger.warning(
                "Website fetch failed for '%s' (attempt %d/%d): %s",
                url,
                attempt_number,
                config.MAX_RETRIES,
                exc,
            )

        try:
            return retry(
                attempt,
                attempts=config.MAX_RETRIES,
                wait_ms=config.RETRY_WAIT_MS,
                exceptions=(requests.exceptions.RequestException,),
                on_retry=on_retry,
            )
        except requests.exceptions.RequestException:
            logger.warning("Giving up on '%s' after %d attempts.", url, config.MAX_RETRIES)
            return ""

    @staticmethod
    def _fetch_page(url: str) -> str:
        """Fetch a page's HTML content via a plain HTTP GET request.

        Args:
            url: The absolute URL to fetch.

        Returns:
            The response HTML.

        Raises:
            requests.exceptions.RequestException: On network failure or
                timeout, so the caller's retry logic can act on it.
        """
        response = requests.get(
            url,
            headers=_REQUEST_HEADERS,
            timeout=config.EMAIL_TIMEOUT,
            allow_redirects=True,
        )
        if response.status_code >= 400:
            return ""
        return response.text