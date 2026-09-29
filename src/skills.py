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
