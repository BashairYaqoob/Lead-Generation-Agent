# AI Lead Generation Agent

An AI-powered agent that accepts a natural language prompt (e.g. *"Find coffee
shops in Karachi"*), extracts the business category and location, uses
browser automation to search Google Maps, scrapes business details,
discovers contact emails, and exports everything to a formatted Excel file.

## Architecture
```
User Prompt
|
v
PromptParser ----> SearchQuery(business_type, location)
|
v
BrowserAgent (Playwright/Chromium)
| launch -> search -> collect_businesses -> open_result (with retries)
v
BusinessScraper
| scrape Google Maps fields -> visit website -> extract_email (with retries)
v
list[Lead]
|
v
ExcelExporter ----> output/leads_<business_type>.xlsx
|
v
RunResult (stats) ----> console summary
```
## Features

- **Natural language prompt parsing** — extracts business type and location.
- **Browser automation** — Playwright-driven Chromium, headless or visible.
- **Google Maps search** — scrolls the results feed to collect multiple
  businesses per run.
- **Reliable navigation** — each business result is scrolled into view,
  waited on, clicked, and confirmed to have actually loaded new content
  before scraping; failures are retried automatically.
- **Stable selectors** — primarily role/aria-label/accessible-name based,
  with generated-class-name fallbacks kept to a minimum.
- **Email extraction** — visits each business's website (homepage plus
  contact/about pages), retrying transient network failures.
- **Excel export** — bold + frozen header row, auto-filter, auto-sized
  columns, true blank cells for missing data, full Unicode support.
- **Detailed summary & logging** — per-business progress, retry warnings,
  and a final report with success/skip counts and execution time.
- **Resilient by design** — a single failed business, website, or email
  lookup never stops the rest of the run; the browser always closes and
  the Excel file always attempts to save.

## Installation

```bash
cd lead-generation-agent
python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
playwright install
cp .env.example .env
```

## Configuration

| Variable            | Description                                                   | Default  |
|---------------------|-----------------------------------------------------------------|----------|
| `HEADLESS`          | Run Chromium without a visible window (`true`/`false`)          | `true`   |
| `MAX_LEADS`         | Maximum businesses to collect per search                           | `20`     |
| `SEARCH_TIMEOUT`    | Timeout (ms) for page loads/selectors                              | `30000`  |
| `MAX_RETRIES`       | Retry attempts for opening businesses, websites, and emails          | `3`      |
| `RETRY_WAIT_MS`     | Wait (ms) between retry attempts                                     | `800`    |
| `EMAIL_TIMEOUT`     | Timeout (seconds) per website request during email search           | `8`      |
| `MAX_CONTACT_PAGES` | Max additional contact/about pages checked per website               | `4`      |
| `OUTPUT_DIRECTORY`  | Folder where Excel files are saved                                   | `output` |

## Running

```bash
python main.py
```
Enter a search query, e.g. 'Find coffee shops in Karachi'

Find gyms in Karachi


### Sample Output
Launching browser...
Searching Google Maps...
Loading businesses...
Business 1/20
Extracting details...
Extracting website...
Searching for email...
✓ Success

Business 2/20
...
========================================
Lead Generation Completed

Query:
Gyms in Karachi

Businesses Processed:
20

Successful:
16

Skipped:
4

Emails Found:
13

Phone Numbers:
18

Websites:
15

Excel File:
output/leads_gyms.xlsx

Execution Time:
32.6 seconds

========================================
Excel files are saved in `output/` as `leads_<business_type>.xlsx` (e.g.
`leads_gyms.xlsx`), with columns: **Business Name, Email, Phone Number,
Website, Location**.

## Limitations

- **Google Maps DOM changes**: Google periodically restructures Maps' HTML
  and generated CSS class names. Selectors here favor ARIA roles and
  accessible names specifically to survive most such changes, but a few
  (e.g. the website link's `data-item-id="authority"`) have no reliable
  accessible-name alternative and may still break if Google changes them.
  If scraping starts failing broadly, check `output/debug/search_timeout.png`
  (auto-saved on a search timeout) first, then review the selector
  constants at the top of `browser.py` and `scraper.py`.
- **Rate limiting / CAPTCHAs**: Very large `MAX_LEADS` values or rapid
  repeated runs may trigger Google's own rate limiting or a CAPTCHA
  challenge, which this project does not attempt to solve or bypass.
- **Email discovery is best-effort**: many small businesses simply don't
  publish an email anywhere on their site, in which case the field is
  correctly left blank rather than guessed.

## Future Improvements

- Support an alternate target site (e.g. Bing Maps) as a fallback when
  Google Maps blocks or rate-limits a session.
- LLM-based prompt parsing for more complex or ambiguous queries.
- Parallel website/email lookups to reduce total execution time.
- Optional CSV export alongside Excel.

## Project Structure
```
lead-generation-agent/
├── main.py # CLI entry point + summary printing
├── agent.py # LeadGenerationAgent orchestration + RunResult stats
├── parser.py # PromptParser: extracts business type + location
├── models.py # SearchQuery and Lead dataclasses
├── config.py # Environment variable configuration
├── browser.py # BrowserAgent: Playwright/Google Maps automation
├── scraper.py # BusinessScraper: business details + email discovery
├── excel_export.py # ExcelExporter: formatted .xlsx writer
├── utils.py # Filenames, logging, timestamps, retry helper
├── output/ # Generated Excel files + debug/ screenshots
├── README.md
├── requirements.txt
├── .env.example
└── .gitignore
```