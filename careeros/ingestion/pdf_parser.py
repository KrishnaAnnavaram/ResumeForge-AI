"""PDF text extraction using pdfplumber."""
from careeros.core.logging import get_logger

log = get_logger(__name__)


def parse_pdf(file_path: str) -> str:
    """Extract raw text from PDF file."""
    try:
        import pdfplumber
    except ImportError:
        raise RuntimeError("pdfplumber is required for PDF parsing: pip install pdfplumber")

    text_parts = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

    full_text = "\n\n".join(text_parts)
    log.info("pdf_parser.complete", file_path=file_path, pages=len(text_parts), chars=len(full_text))
    return full_text
