"""Command-line entry point for the Lead Generation Agent.

Prompts the user for a natural language search query, runs the full agent
workflow (search, scrape, email discovery, Excel export), and prints a
detailed final summary.
"""

from agent import LeadGenerationAgent, RunResult
from utils import configure_logging

logger = configure_logging()


def print_summary(result: RunResult) -> None:
    """Print a detailed final summary of the lead generation run.

    Args:
        result: The RunResult produced by LeadGenerationAgent.run().
    """
    print("\n" + "=" * 40)
    print("Lead Generation Completed")
    print("=" * 40)
    print(f"\nQuery:\n{result.query.business_type.title()} in {result.query.location}")
    print(f"\nBusinesses Processed:\n{result.businesses_processed}")
    print(f"\nSuccessful:\n{result.successful}")
    print(f"\nSkipped:\n{result.skipped}")
    print(f"\nEmails Found:\n{result.emails_found}")
    print(f"\nPhone Numbers:\n{result.phones_found}")
    print(f"\nWebsites:\n{result.websites_found}")
    print(f"\nExcel File:\n{result.excel_path or '(not saved - no leads collected or save failed)'}")
    print(f"\nExecution Time:\n{result.execution_time_seconds} seconds")
    print("\n" + "=" * 40)


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