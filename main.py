"""Command-line entry point for the Lead Generation Agent.

Prompts the user for a natural language search query, runs the full agent
workflow (search, scrape, email discovery, Excel export), and prints a
final summary.
"""

from agent import LeadGenerationAgent, RunResult
from utils import configure_logging

logger = configure_logging()


def print_summary(result: RunResult) -> None:
    """Print a clean final summary of the lead generation run.

    Args:
        result: The RunResult produced by LeadGenerationAgent.run().
    """
    print("\n" + "=" * 40)
    print("Lead Generation Complete")
    print("=" * 40)
    print(f"Search Query: {result.query.business_type.title()} in {result.query.location}")
    print(f"Businesses Found: {len(result.leads)}")
    print(f"Emails Found: {result.emails_found}")

    if result.excel_path:
        print(f"Excel File: {result.excel_path}")
    else:
        print("Excel File: (not saved - no leads collected or save failed)")

    print("=" * 40)


def main() -> None:
    """Run the CLI application."""
    print("=" * 50)
    print("AI Lead Generation Agent")
    print("=" * 50)
    print("Enter a search query, e.g. 'Find coffee shops in Karachi'\n")

    prompt = input("> ").strip()

    if not prompt:
        print("No prompt entered. Exiting.")
        return

    agent = LeadGenerationAgent()

    try:
        result = agent.run(prompt)
    except ValueError as exc:
        logger.error("Failed to parse prompt: %s", exc)
        print(f"\nError: {exc}")
        return
    except Exception as exc:  # noqa: BLE001 - top-level safety net for the CLI
        logger.error("Unexpected error during run: %s", exc)
        print(f"\nAn unexpected error occurred: {exc}")
        return

    print_summary(result)


if __name__ == "__main__":
    main()