import re
from pathlib import Path

from openpyxl import load_workbook
from pypdf import PdfReader

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".xlsx", ".xls"}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _extract_pdf(path: Path) -> list[tuple[str, str]]:
    reader = PdfReader(str(path))
    return [
        (str(i + 1), _normalize(page.extract_text() or ""))
        for i, page in enumerate(reader.pages)
    ]


def _extract_text_file(path: Path) -> list[tuple[str, str]]:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    return [("1", _normalize(raw))]


def _extract_xlsx(path: Path) -> list[tuple[str, str]]:
    wb = load_workbook(str(path), data_only=True, read_only=True)
    sections = []
    for sheet in wb.worksheets:
        rows_text = []
        for row in sheet.iter_rows(values_only=True):
            cells = [str(c) for c in row if c is not None]
            if cells:
                rows_text.append(" | ".join(cells))
        if rows_text:
            sections.append((sheet.title, _normalize("\n".join(rows_text))))
    return sections


_EXTRACTORS = {
    ".pdf": _extract_pdf,
    ".txt": _extract_text_file,
    ".md": _extract_text_file,
    ".xlsx": _extract_xlsx,
    ".xls": _extract_xlsx,
}


def extract_sections(path: Path) -> list[tuple[str, str]]:
    """Returns [(location_label, text), ...] — page number for PDF, sheet name for
    Excel, "1" for flat text files. Raises ValueError for unsupported extensions."""
    ext = path.suffix.lower()
    extractor = _EXTRACTORS.get(ext)
    if extractor is None:
        raise ValueError(f"Unsupported file type: {ext}")
    return extractor(path)
