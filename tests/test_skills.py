"""
test_skills.py
---------------
Simple tests for the skill-extraction logic. These don't need the
embedding model or internet access, so they run instantly — good for
checking the "explainable" part of the project actually works correctly.

Run with:
    python -m pytest tests/
"""

import sys
import os

# Make sure "src" is importable when running this test file directly.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.skills import extract_skills


def test_finds_exact_skill():
    text = "I have 3 years of experience with Python and SQL."
    found = extract_skills(text)
    assert "python" in found
    assert "sql" in found


def test_case_insensitive():
    text = "Experienced in PYTHON and Docker."
    found = extract_skills(text)
    assert "python" in found
    assert "docker" in found


def test_whole_word_only():
    # "r" should NOT match inside "framework" or "docker"
    text = "I built a web framework using Docker."
    found = extract_skills(text)
    assert "r" not in found


def test_no_false_positive_on_unrelated_text():
    text = "The weather today is sunny and warm."
    found = extract_skills(text)
    assert found == set()


def test_special_characters_like_cpp():
    text = "Proficient in C++ and Java."
    found = extract_skills(text)
    assert "c++" in found
    assert "java" in found


if __name__ == "__main__":
    test_finds_exact_skill()
    test_case_insensitive()
    test_whole_word_only()
    test_no_false_positive_on_unrelated_text()
    test_special_characters_like_cpp()
    print("All tests passed!")
