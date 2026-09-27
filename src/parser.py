"""
parser.py
---------
This file has ONE job: take a resume file (PDF, DOCX, or TXT) and pull out
the plain text so the rest of the program can work with it.

Why separate this into its own file? So that if you later want to support
another format (e.g. .rtf), you only touch this file — nothing else in the
project needs to change. This is called "separation of concerns."
"""

import os
import fitz  # this is the import name for the PyMuPDF library
import docx


def extract_text_from_pdf(file_path):
    """Reads every page of a PDF and returns all the text as one string."""
    text = ""
    document = fitz.open(file_path)
    for page in document:
        text += page.get_text()
    document.close()
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
    This pattern (checking the extension once, then dispatching) is called
    a "dispatcher" — it keeps the messy if/else logic in one place.
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
