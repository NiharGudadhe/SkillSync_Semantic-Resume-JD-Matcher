import os
from pypdf import PdfReader
import docx


def extract_text_from_pdf(file_path):
    """Reads every page of a PDF and returns all the text as one string."""
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text


def extract_text_from_docx(file_path):
    """Reads a .docx file paragraph by paragraph and joins them together."""
    document = docx.Document(file_path)
    paragraphs = [p.text for p in document.paragraphs]
    return "\n".join(paragraphs)


def extract_text_from_txt(file_path):
    """Reads a plain .txt file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def extract_text(file_path):
    """
    Looks at the file extension and calls the right extractor function.
    """
    extension = os.path.splitext(file_path)[1].lower()

    if extension == ".pdf":
        return extract_text_from_pdf(file_path)
    elif extension == ".docx":
        return extract_text_from_docx(file_path)
    elif extension == ".txt":
        return extract_text_from_txt(file_path)
    else:
        raise ValueError(
            f"Unsupported file type: '{extension}'. Please use PDF, DOCX, or TXT."
        )