# AI Lead Generation Agent

An AI-powered agent that accepts a natural language prompt (e.g. *"Find coffee
shops in Karachi"*), extracts the business category and location, uses
browser automation to search Google Maps, and collects visible business
details. Email extraction and Excel export will be added in later stages.

## Current Stage: Browser Automation (Playwright)

This stage adds:

- `browser.py` — `BrowserAgent`: launches Chromium, searches Google Maps,
  scrolls to load multiple results, and opens each business's detail pane.
- `scraper.py` — `BusinessScraper`: extracts business name, phone number,
  website, and address from the open detail pane into a `Lead`.
- Updated `agent.py` to orchestrate the full search → scrape workflow.
- Updated `main.py` to print all collected leads.

**Email extraction and Excel export are NOT implemented yet.**

## Folder Structure
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

This downloads the Chromium build Playwright uses; it's a one-time setup
step separate from `pip install`.

### 5. Configure environment variables

Copy the example file and edit as needed:

```bash
cp .env.example .env
```

## Configuration

| Variable        | Description                                              | Default |
|-----------------|-----------------------------------------------------------|---------|
| `HEADLESS`      | Run Chromium without a visible window (`true`/`false`)    | `true`  |
| `MAX_LEADS`     | Maximum number of businesses to collect per search         | `20`    |
| `SEARCH_TIMEOUT`| Timeout in milliseconds for page loads/selectors           | `15000` |

To watch the browser while it works (useful for debugging selectors), set:

HEADLESS=false

To collect more or fewer leads per run, adjust:

MAX_LEADS=10

## Running the Project

From the project root, run:

```bash
python main.py
```

You will be prompted to enter a search query:

Enter a search query, e.g. 'Find coffee shops in Karachi'

Find coffee shops in Karachi

The agent will:

1. Parse the business type and location from your prompt.
2. Launch Chromium and open Google Maps.
3. Search for the business type + location.
4. Scroll to load up to `MAX_LEADS` results.
5. Open each result and extract its name, phone, website, and address.
6. Print all collected leads.

Example output:

Found 10 businesses

Business Name: ABC Coffee
Phone: 021-xxxxxxx
Website: https://example.com
Location: Karachi, Pakistan

## Example Prompts

- `Find coffee shops in Karachi`
- `I need dentists in Chicago`
- `Software houses in Lahore`
- `Show me bakeries in New York`

## Notes on Reliability

Google Maps' HTML structure changes periodically, and its selectors
(defined at the top of `browser.py` and `scraper.py`) may need updating if
scraping stops working. Both modules are designed so any missing field
degrades gracefully to an empty string rather than crashing the program.

## What's Next

1. **Email Extraction** — Visit each business's website (from the
   `website` field) and search common pages (Home, Contact, About) for a
   contact email address.
2. **Excel Export** — Implement `excel_export.py` to write all collected
   leads to a `.xlsx` file in `output/`, with columns for Business Name,
   Email, Phone Number, Website, and Location.
3. **Full Agent Workflow** — Wire Excel export into `agent.run()` and print
   a final summary (search query, lead count, output file path).
