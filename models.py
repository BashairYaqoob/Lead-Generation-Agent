"""Data models for the Lead Generation Agent.

This module defines the core dataclasses used throughout the application:
- SearchQuery: represents a parsed user request (business type + location).
- Lead: represents a single collected business lead.
"""

from dataclasses import dataclass, field


@dataclass
class SearchQuery:
    """Represents a parsed search request extracted from a natural language prompt.

    Attributes:
        business_type: The type/category of business to search for (e.g. "coffee shops").
        location: The target location for the search (e.g. "Karachi").
    """

    business_type: str
    location: str

    def __post_init__(self) -> None:
        """Normalize whitespace in the fields after initialization."""
        self.business_type = self.business_type.strip()
        self.location = self.location.strip()

    def __str__(self) -> str:
        """Return a human-readable representation of the search query."""
        return f"{self.business_type} in {self.location}"


@dataclass
class Lead:
    """Represents a single business lead collected by the agent.

    All fields default to empty strings except `location`, which is typically
    known ahead of time from the originating SearchQuery. This ensures that
    missing data (e.g. no email found) never causes the program to crash.

    Attributes:
        business_name: The name of the business.
        email: The business's email address, if found.
        phone_number: The business's phone number, if found.
        website: The business's website URL, if found.
        location: The location associated with this lead.
    """

    business_name: str = ""
    email: str = ""
    phone_number: str = ""
    website: str = ""
    location: str = field(default="")

    def is_complete(self) -> bool:
        """Check whether all fields of this lead have been populated.

        Returns:
            True if business_name, email, phone_number, and website are all
            non-empty, False otherwise.
        """
        return all(
            [
                self.business_name,
                self.email,
                self.phone_number,
                self.website,
            ]
        )

    def to_dict(self) -> dict[str, str]:
        """Convert the lead into a plain dictionary, useful for export.

        Returns:
            A dictionary mapping column names to values, matching the
            expected Excel export column order.
        """
        return {
            "Business Name": self.business_name,
            "Email": self.email,
            "Phone Number": self.phone_number,
            "Website": self.website,
            "Location": self.location,
        }