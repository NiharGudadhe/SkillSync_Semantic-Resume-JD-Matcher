"""
skills.py
---------
A simple, EXPLAINABLE way to find skills mentioned in text: we keep a list
of known skill keywords/phrases and check which ones appear in the text.

This is a lookup approach, not a trained NER model. That is a deliberate
choice, not a shortcut:
  - It needs no training data or GPU.
  - It runs instantly.
  - You can explain EXACTLY how it works in an interview — no black box.

If you want to extend this later, the natural upgrade path is spaCy's NER
or a fine-tuned transformer — but for a first version, a keyword list gets
you 80% of the value for 5% of the effort.
"""

import re

# A starter list — feel free to add more skills relevant to the roles
# you're targeting. Keep entries lowercase; matching is case-insensitive.
SKILL_KEYWORDS = [
    # Programming languages
    "python", "sql", "java", "javascript", "typescript", "c++",
    # Machine learning / statistics
    "machine learning", "deep learning", "regression", "classification",
    "clustering", "time series", "random forest", "xgboost", "lightgbm",
    "scikit-learn", "pandas", "numpy", "tensorflow", "pytorch", "keras",
    "feature engineering", "hyperparameter tuning", "cross-validation",
    "smote", "anomaly detection",
    # NLP
    "nlp", "natural language processing", "tokenization", "word embeddings",
    "named entity recognition", "ner", "sentiment analysis", "transformers",
    "bert", "huggingface", "spacy", "nltk", "langchain", "rag", "llm",
    "prompt engineering", "tf-idf",
    # Computer vision
    "computer vision", "opencv", "yolo", "image classification",
    "object detection", "image segmentation",
    # Databases
    "postgresql", "mysql", "mongodb", "redis",
    # Engineering / deployment
    "fastapi", "flask", "django", "docker", "kubernetes", "git", "github",
    "ci/cd", "aws", "azure", "gcp", "linux", "streamlit",
    # BI / visualization
    "power bi", "tableau", "excel", "dax",
    # Data engineering
    "etl", "elt", "dbt", "airflow", "spark", "pyspark", "databricks",
    "data warehousing",
    # MLOps
    "mlflow", "evidently", "model monitoring", "drift detection",
]


def extract_skills(text, skill_list=None):
    """
    Scans `text` and returns the SET of skills (from skill_list) found in it.

    Matching rules:
    - Case-insensitive ("Python" and "python" both match).
    - Whole-word/whole-phrase only, so short skills like "r" don't
      accidentally match inside unrelated words like "framework".
    """
    if skill_list is None:
        skill_list = SKILL_KEYWORDS

    text_lower = text.lower()
    found = set()

    for skill in skill_list:
        skill_lower = skill.lower()
        # (?<![a-z0-9]) and (?![a-z0-9]) are "boundary checks" — they make
        # sure there isn't a letter/number touching the match on either
        # side, so we get whole-word matches even for skills containing
        # special characters like "c++" or "ci/cd".
        pattern = r"(?<![a-z0-9])" + re.escape(skill_lower) + r"(?![a-z0-9])"
        if re.search(pattern, text_lower):
            found.add(skill)

    return found
