# SkillSync ↔ Semantic Resume-JD Matcher

A small, fully self-built NLP project: upload a resume, paste a job
description, and get a match score based on **meaning** (semantic
similarity) rather than just matching keywords.

This project extends the TF-IDF + classifier approach used in an earlier
sentiment-analysis project by upgrading to **dense embeddings** for
similarity comparison — a natural, honest next step in an NLP skill
progression.

---

## 1. What it does

1. You upload a resume (PDF, DOCX, or TXT).
2. You paste in a job description.
3. The app:
   - Converts both texts into number vectors ("embeddings") using a
     pretrained sentence-embedding model.
   - Compares those vectors using **cosine similarity** to get a
     meaning-based match score.
   - Separately scans both texts for known skill keywords and reports
     which skills match, which are missing, and which are extra.
   - Combines both signals into one overall match percentage.

---

## 2. Project structure

```
resume-jd-matcher/
├── app.py                  # Streamlit web app (the UI)
├── requirements.txt        # Python packages needed
├── src/
│   ├── __init__.py
│   ├── parser.py           # Extracts text from PDF/DOCX/TXT
│   ├── skills.py           # Keyword-based skill extraction
│   └── matcher.py          # Embeddings + similarity + scoring logic
├── sample_data/
│   ├── sample_resume.txt   # Try the app without needing a real PDF
│   └── sample_jd.txt
└── tests/
    └── test_skills.py      # Quick tests for the skill extractor
```
