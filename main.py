"""Command-line entry point for the Lead Generation Agent.

Prompts the user for a natural language search query, runs the agent's
search + scrape workflow, and prints the collected leads.
"""

from agent import LeadGenerationAgent
from models import Lead
from utils import configure_logging

logger = configure_logging()


def print_leads(leads: list[Lead]) -> None:
    """Print collected leads in a clean, human-readable format.

    Args:
        leads: The list of Lead objects to display.
    """
    print(f"\nFound {len(leads)} businesses\n")

    for position, lead in enumerate(leads, start=1):
        print(f"{position}.")
        print(f"Business Name: {lead.business_name or '(not found)'}")
        print(f"Phone: {lead.phone_number or '(not found)'}")
        print(f"Website: {lead.website or '(not found)'}")
        print(f"Location: {lead.location or '(not found)'}")
        print("-" * 20)


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
        leads = agent.run(prompt)
    except ValueError as exc:
        logger.error("Failed to parse prompt: %s", exc)
        print(f"\nError: {exc}")
        return
    except TimeoutError as exc:
        logger.error("Browser automation timed out: %s", exc)
        print(f"\nError: {exc}")
        return
    except RuntimeError as exc:
        logger.error("Browser automation failed: %s", exc)
        print(f"\nError: {exc}")
        return

    print_leads(leads)
    print(
        "\nNote: Email extraction and Excel export are not yet implemented. "
        "This will be added in the next development stage."
    )


if __name__ == "__main__":
    main()