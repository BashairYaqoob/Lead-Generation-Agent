# AI Lead Generation Agent

An AI-powered agent that accepts a natural language prompt (e.g. *"Find coffee
shops in Karachi"*), extracts the business category and location, uses
browser automation to search Google Maps, scrapes business details, discovers
contact emails, and exports everything to an Excel file.

## Features

- **Natural language prompt parsing** — extracts business type and location
  from prompts like `"Find coffee shops in Karachi"`.
- **Browser automation** — Playwright-driven Chromium session, headless or
  visible.
- **Google Maps search** — searches and scrolls the results feed to collect
  multiple businesses per run.
- **Business scraping** — extracts business name, phone number, website, and
  address from each result.
- **Email extraction** — visits each business's website (homepage plus
  contact/about pages) and searches for a contact email address using a
  regular expression.
- **Excel export** — saves all collected leads to a `.xlsx` file with
  auto-sized columns.
- **Error handling** — missing fields, unreachable websites, timeouts, or a
  single failed business never stop the overall run.

## Project Structure
```
lead-generation-agent/
├── main.py # CLI entry point
├── agent.py # LeadGenerationAgent orchestration class
├── parser.py # PromptParser: extracts business type + location
├── models.py # SearchQuery and Lead dataclasses
├── config.py # Environment variable configuration
├── browser.py # BrowserAgent: Playwright/Google Maps automation
├── scraper.py # BusinessScraper: extracts lead details
├── excel_export.py # Excel export (stub, future stage)
├── utils.py # Generic helpers (filenames, logging, timestamps)
├── output/ # Generated Excel files will be saved here
│ └── .gitkeep
├── README.md
├── requirements.txt
├── .env.example
└── .gitignore
```

## Installation

### 1. Clone or download the project

```bash
cd lead-generation-agent
```

### 2. Create and activate a virtual environment

**macOS / Linux:**

```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows:**

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Playwright's browser binaries

```bash
playwright install
```

### 5. Configure environment variables

```bash
cp .env.example .env
```

## Configuration

| Variable            | Description                                                   | Default  |
|---------------------|-----------------------------------------------------------------|----------|
| `HEADLESS`          | Run Chromium without a visible window (`true`/`false`)          | `true`   |
| `MAX_LEADS`         | Maximum number of businesses to collect per search                | `20`     |
| `SEARCH_TIMEOUT`    | Timeout in milliseconds for page loads/selectors                  | `15000`  |
| `EMAIL_TIMEOUT`     | Timeout in seconds for each website request during email search   | `8`      |
| `MAX_CONTACT_PAGES` | Max additional contact/about pages checked per website             | `4`      |
| `OUTPUT_DIRECTORY`  | Folder where Excel files are saved                                 | `output` |

## Running the Project

```bash
python main.py
```

Enter a prompt when asked:
Enter a search query, e.g. 'Find coffee shops in Karachi'

Find coffee shops in Karachi


The agent will parse the prompt, search Google Maps, collect businesses,
attempt to find each one's contact email, save an Excel file, and print a
summary:
```
========================================
Lead Generation Complete
Search Query: Coffee Shops in Karachi
Businesses Found: 18
Emails Found: 11
Excel File: output/leads_coffee_shops.xlsx
```
## Output

Excel files are saved in the `output/` directory using the pattern:
leads_<business_type>.xlsx


Examples: `leads_coffee_shops.xlsx`, `leads_dentists.xlsx`,
`leads_software_houses.xlsx`.

Each file contains one row per lead with the columns: **Business Name,
Email, Phone Number, Website, Location**.

## Example Prompts

- `Find coffee shops in Karachi`
- `I need dentists in Chicago`
- `Software houses in Lahore`
- `Show me bakeries in New York`

## Notes on Reliability

- Google Maps' HTML structure changes periodically; selectors are
  centralized at the top of `browser.py` and `scraper.py` for easy updates.
- Email discovery uses plain HTTP requests (not Playwright) against each
  business's homepage plus a small, bounded set of contact/about pages, so
  a slow or unreachable website never blocks the browser session.
- Any missing field (email, phone, website, address) is left as an empty
  string; a failure on one business is logged and skipped without stopping
  the rest of the run.

## Assignment Requirements Checklist

| Requirement | Status | Where it's implemented |
|---|---|---|
| Accepts a natural-language prompt describing lead type + location | ✅ | `main.py` CLI input, `parser.py` |
| Extracts business category and location from the prompt | ✅ | `PromptParser.parse()` in `parser.py` |
| Uses browser automation on a map/business listing site | ✅ | `BrowserAgent` in `browser.py` (Playwright + Google Maps) |
| Searches based on parsed category + location | ✅ | `LeadGenerationAgent.search_businesses()` in `agent.py` |
| Collects business name, email, phone, website | ✅ | `BusinessScraper.scrape()` in `scraper.py` |
| Collects multiple leads, not just one | ✅ | `BrowserAgent.collect_businesses()` scrolls to load up to `MAX_LEADS` results |
| Missing fields left blank instead of crashing | ✅ | All extraction helpers in `scraper.py` return `""` on failure; never raise |
| Leads saved into an `.xlsx` file | ✅ | `ExcelExporter.export()` in `excel_export.py` |
| Excel file has clear columns (Business Name, Email, Phone Number, Website, Location) | ✅ | `_COLUMN_HEADERS` in `excel_export.py` |
| Meaningful, sanitized filename | ✅ | `leads_<business_type>.xlsx` via `sanitize_filename()` in `utils.py`, used in `agent.py` |
| Prints a clear summary (query, lead count, file path) | ✅ | `print_summary()` in `main.py` |
| Runs without runtime errors given valid setup | ✅ | Errors caught at every stage (parsing, browser, scraping, email fetch, Excel save) |
| README explains install, config, running, and output location | ✅ | This file |
| Complete source code, no generated dependency folders submitted | ✅ | `.gitignore` excludes `venv/`, `node_modules/`, `.env` |