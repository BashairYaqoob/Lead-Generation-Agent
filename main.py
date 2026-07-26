"""Command-line entry point for the Lead Generation Agent.

Prompts the user for a natural language search query, runs the current
(partial) agent workflow, and prints the parsed business type and location.
"""

from agent import LeadGenerationAgent
from utils import configure_logging

logger = configure_logging()


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
        query = agent.run(prompt)
    except ValueError as exc:
        logger.error("Failed to parse prompt: %s", exc)
        print(f"\nError: {exc}")
        return

    print("\nParsed Search Query")
    print("-" * 50)
    print(f"Business Type : {query.business_type}")
    print(f"Location      : {query.location}")
    print("-" * 50)
    print(
        "\nNote: Business search, scraping, and Excel export are not yet "
        "implemented. This will be added in the next development stage."
    )


if __name__ == "__main__":
    main()