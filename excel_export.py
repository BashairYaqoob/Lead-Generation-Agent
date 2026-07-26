"""Excel export module (stub).

This module will contain logic for writing collected Lead objects to an
.xlsx file using openpyxl or pandas.

Not implemented yet. This is a placeholder to establish the module boundary
for the next development stage.
"""

from models import Lead


class ExcelExporter:
    """Exports a list of Lead objects to an Excel (.xlsx) file."""

    def export(self, leads: list[Lead], filename: str) -> str:
        """Export leads to an Excel file.

        Args:
            leads: The list of Lead objects to export.
            filename: The desired output filename (without or with .xlsx).

        Returns:
            The full path to the saved Excel file.

        Raises:
            NotImplementedError: Excel export is not yet implemented.
        """
        raise NotImplementedError("Excel export will be implemented in a later stage.")