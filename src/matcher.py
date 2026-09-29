import numpy as np
from sentence_transformers import SentenceTransformer

from .skills import extract_skills

# Loading the embedding model is slow (a few seconds), so we load it ONCE
# and reuse it for every comparison instead of reloading every time.
_MODEL_NAME = "all-MiniLM-L6-v2"  # small (~80MB), fast on CPU, good accuracy
_model = None


def get_model():
    """Loads the embedding model the first time it's needed, then reuses it."""
    global _model
    if _model is None:
        _model = SentenceTransformer(_MODEL_NAME)
    return _model


def cosine_similarity(vector_a, vector_b):
    """
    Cosine similarity measures how similar the DIRECTION of two vectors is,
    ignoring their length/magnitude. For sentence embeddings this gives a
    score from 0 (unrelated meaning) to 1 (identical meaning).

    Formula: (A . B) / (|A| * |B|)
    """
    dot_product = np.dot(vector_a, vector_b)
    norm_a = np.linalg.norm(vector_a)
    norm_b = np.linalg.norm(vector_b)
    return dot_product / (norm_a * norm_b)


def semantic_similarity(resume_text, jd_text):
    """Embeds both texts and returns their cosine similarity, clipped to [0, 1]."""
    model = get_model()
    embeddings = model.encode([resume_text, jd_text])
    score = cosine_similarity(embeddings[0], embeddings[1])
    return float(max(0.0, min(1.0, score)))


def skill_overlap_score(resume_skills, jd_skills):
    """
    What fraction of the JD's requested skills does the resume cover?

    This is deliberately asymmetric — we score against what the JOB needs,
    not against how many extra skills the resume happens to list. A
    resume with 50 irrelevant skills shouldn't outscore one that matches
    the actual role better.
    """
    if not jd_skills:
        return 0.0
    matched = resume_skills & jd_skills  # set intersection
    return len(matched) / len(jd_skills)


def match(resume_text, jd_text, semantic_weight=0.6, skill_weight=0.4):
    """
    Runs the full comparison. Returns a dictionary with:
      overall_score   - 0-100, the final blended match percentage
      semantic_score  - 0-100, meaning-based similarity
      skill_score     - 0-100, fraction of JD skills found in the resume
      matched_skills  - skills present in both
      missing_skills  - skills the JD wants but the resume doesn't mention
      extra_skills    - skills the resume has that the JD didn't ask for
    """
    sem_score = semantic_similarity(resume_text, jd_text)

    resume_skills = extract_skills(resume_text)
    jd_skills = extract_skills(jd_text)
    sk_score = skill_overlap_score(resume_skills, jd_skills)

    overall = (semantic_weight * sem_score) + (skill_weight * sk_score)

    return {
        "overall_score": round(overall * 100, 1),
        "semantic_score": round(sem_score * 100, 1),
        "skill_score": round(sk_score * 100, 1),
        "matched_skills": sorted(resume_skills & jd_skills),
        "missing_skills": sorted(jd_skills - resume_skills),
        "extra_skills": sorted(resume_skills - jd_skills),
    }
