# AI Lead Generation Agent

An AI-powered agent that accepts a natural language prompt (e.g. *"Find coffee
shops in Karachi"*), extracts the business category and location, and — in
later stages — will use browser automation to search a map/business listing
website, scrape lead information, and export the results to an Excel file.

## Current Stage: Foundation & Architecture

This stage sets up the project's core architecture:

- Data models (`SearchQuery`, `Lead`)
- Configuration loading via `.env`
- Rule-based prompt parsing (business type + location extraction)
- Agent orchestration skeleton
- CLI entry point

**Browser automation, web scraping, and Excel export are NOT implemented
yet.** These will be added in the next development stage using Playwright,
BeautifulSoup, and openpyxl.

## Folder Structure
```
lead-generation-agent/
├── main.py # CLI entry point
├── agent.py # LeadGenerationAgent orchestration class
├── parser.py # PromptParser: extracts business type + location
├── models.py # SearchQuery and Lead dataclasses
├── config.py # Environment variable configuration
├── browser.py # Browser automation (stub, future stage)
├── scraper.py # Business scraping (stub, future stage)
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

### 4. Configure environment variables

Copy the example file and edit as needed:

```bash
cp .env.example .env
```

At this stage, the default values in `.env.example` are sufficient — no
API key is required yet since the parser is rule-based.

## Running the Project

From the project root, run:

```bash
python main.py
```

You will be prompted to enter a search query:
Enter a search query, e.g. 'Find coffee shops in Karachi'

coffee shops in Karachi


The agent will parse the prompt and print the extracted business type and
location:
Parsed Search Query
Business Type : coffee shops
Location : Karachi

## Example Prompts

- `Find coffee shops in Karachi`
- `I need dentists in Chicago`
- `Software houses in Lahore`
- `Show me bakeries in New York`

## What's Next

The following stages will build on this foundation:

1. **Browser Automation** — Implement `browser.py` using Playwright to
   navigate and search a map/business listing website (e.g. Google Maps or
   Bing Maps).
2. **Scraping** — Implement `scraper.py` to extract business name, phone
   number, website, and (where possible) email address for each result.
3. **Excel Export** — Implement `excel_export.py` to write all collected
   leads to a `.xlsx` file in the `output/` directory, with columns for
   Business Name, Email, Phone Number, Website, and Location.
4. **Full Agent Workflow** — Wire everything together in `agent.run()` so
   the CLI performs the complete search → scrape → export pipeline and
   prints a final summary.
