"""Excel export module.

Writes a list of collected Lead objects to an .xlsx file using openpyxl,
with auto-sized columns and a sanitized, descriptive filename.
"""

import os

from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from models import Lead

_COLUMN_HEADERS = ["Business Name", "Email", "Phone Number", "Website", "Location"]

# Minimum and maximum column widths (in characters) used when auto-sizing.
_MIN_COLUMN_WIDTH = 12
_MAX_COLUMN_WIDTH = 60


class ExcelExporter:
    """Exports a list of Lead objects to an Excel (.xlsx) file."""

    def export(self, leads: list[Lead], filename: str) -> str:
        """Export leads to an Excel file with auto-sized columns.

        Args:
            leads: The list of Lead objects to export (may be empty, in
                which case a file with only headers is created).
            filename: The desired output filename or path. If it does not
                already end in ".xlsx", the extension is appended. If it
                is not already inside the output directory, it is joined
                with `config.OUTPUT_DIRECTORY`.

        Returns:
            The full path to the saved Excel file.

        Raises:
            OSError: If the file cannot be written (e.g. permissions
                issue, invalid path, disk full).
        """
        full_path = self._resolve_output_path(filename)

        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Leads"

        self._write_headers(worksheet)
        self._write_rows(worksheet, leads)
        self._autosize_columns(worksheet)

        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        try:
            workbook.save(full_path)
        except OSError as exc:
            raise OSError(f"Failed to save Excel file to '{full_path}': {exc}") from exc

        return full_path

    @staticmethod
    def _resolve_output_path(filename: str) -> str:
        """Resolve the final output file path for the given filename.

        Args:
            filename: The desired filename, with or without a directory
                or extension.

        Returns:
            An absolute-ish path (relative to the current working
            directory) ending in the output directory and ".xlsx".
        """
        import config

        name = filename.strip()
        if not name.lower().endswith(".xlsx"):
            name = f"{name}.xlsx"

        directory = os.path.dirname(name)
        if directory:
            return name

        return os.path.join(config.OUTPUT_DIRECTORY, name)

    @staticmethod
    def _write_headers(worksheet: Worksheet) -> None:
        """Write the header row with bold styling.

        Args:
            worksheet: The worksheet to write headers into.
        """
        for column_index, header in enumerate(_COLUMN_HEADERS, start=1):
            cell = worksheet.cell(row=1, column=column_index, value=header)
            cell.font = Font(bold=True)

    @staticmethod
    def _write_rows(worksheet: Worksheet, leads: list[Lead]) -> None:
        """Write one row per lead below the header row.

        Args:
            worksheet: The worksheet to write rows into.
            leads: The list of leads to write.
        """
        for row_index, lead in enumerate(leads, start=2):
            data = lead.to_dict()
            for column_index, header in enumerate(_COLUMN_HEADERS, start=1):
                worksheet.cell(row=row_index, column=column_index, value=data.get(header, ""))

    @staticmethod
    def _autosize_columns(worksheet: Worksheet) -> None:
        """Adjust each column's width to roughly fit its longest value.

        Args:
            worksheet: The worksheet whose columns should be resized.
        """
        for column_index, header in enumerate(_COLUMN_HEADERS, start=1):
            column_letter = get_column_letter(column_index)
            max_length = len(header)

            for row in worksheet.iter_rows(
                min_col=column_index, max_col=column_index, min_row=2
            ):
                cell_value = row[0].value
                if cell_value:
                    max_length = max(max_length, len(str(cell_value)))

            width = min(max(max_length + 2, _MIN_COLUMN_WIDTH), _MAX_COLUMN_WIDTH)
            worksheet.column_dimensions[column_letter].width = width