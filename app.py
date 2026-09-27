"""
app.py
------
An interactive Streamlit web app: upload a resume, paste a job
description, and see a visual match breakdown — a color-coded score bar,
skill chips grouped by matched/missing/extra, and a downloadable report.

Run with:
    streamlit run app.py
"""

import os
import tempfile
from datetime import datetime

import streamlit as st

from src.parser import extract_text
from src.matcher import match

st.set_page_config(
    page_title="SkillSync — Resume-JD Matcher",
    page_icon="🧩",
    layout="centered",
)

# ---------------------------------------------------------------- styling
st.markdown(
    """
    <style>
    .chip {
        display: inline-block;
        padding: 4px 12px;
        margin: 4px 4px 4px 0;
        border-radius: 16px;
        font-size: 0.85rem;
        font-weight: 500;
        border: 1px solid;
    }
    .chip-matched { background: #dcfce7; color: #15803d; border-color: #15803d; }
    .chip-missing { background: #fee2e2; color: #b91c1c; border-color: #b91c1c; }
    .chip-extra   { background: #dbeafe; color: #1d4ed8; border-color: #1d4ed8; }
    .score-track {
        background: #e5e7eb;
        border-radius: 999px;
        overflow: hidden;
        height: 32px;
        width: 100%;
    }
    .score-fill {
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: flex-end;
        padding-right: 12px;
        color: white;
        font-weight: 700;
        font-size: 0.95rem;
        white-space: nowrap;
        transition: width 0.4s ease;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def render_chips(skills, css_class):
    """Turns a list of skill strings into small colored pill/chip HTML."""
    if not skills:
        return "<p style='color:#888; font-style: italic;'>None</p>"
    chips_html = "".join(f'<span class="chip {css_class}">{s}</span>' for s in skills)
    return f"<div>{chips_html}</div>"


def score_color(score):
    """Red below 40, orange 40-70, green above 70 — a quick visual read."""
    if score < 40:
        return "#dc2626"
    elif score < 70:
        return "#f59e0b"
    else:
        return "#16a34a"


def render_score_bar(score):
    """A horizontal, color-coded bar showing the overall match percentage."""
    color = score_color(score)
    width = max(score, 8)  # keep a visible sliver even for very low scores
    st.markdown(
        f"""
        <div class="score-track">
            <div class="score-fill" style="width:{width}%; background:{color};">
                {score}%
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def verdict_text(score):
    if score >= 70:
        return "Strong match — this resume aligns well with the job description."
    elif score >= 40:
        return "Moderate match — some important gaps to address."
    else:
        return "Weak match — significant gaps between resume and job description."


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    st.write(
        "The overall score blends two signals. Adjust the balance below "
        "and re-run the analysis to see how the result changes."
    )
    semantic_weight = st.slider("Semantic similarity weight", 0.0, 1.0, 0.6, 0.05)
    skill_weight = round(1.0 - semantic_weight, 2)
    st.caption(f"Skill overlap weight is automatically set to **{skill_weight}**.")

    with st.expander("How it works"):
        st.markdown(
            "- **Semantic similarity**: embeds both texts and compares "
            "meaning using cosine similarity — catches rephrased skills "
            "that don't share exact wording.\n"
            "- **Skill overlap**: checks a known skill-keyword list "
            "against both texts — simple and fully explainable."
        )

# ---------------------------------------------------------------- header
st.title("🧩 SkillSync")
st.caption("Semantic Resume ↔ Job Description Matcher")
st.write(
    "Upload your resume and paste a job description. This tool compares "
    "them using sentence embeddings (meaning-based similarity) plus a "
    "skill-keyword check — not just simple keyword matching."
)

st.divider()

# ---------------------------------------------------------------- inputs
col1, col2 = st.columns(2)

with col1:
    st.subheader("📄 Resume")
    resume_file = st.file_uploader(
        "Upload resume (PDF, DOCX, or TXT)", type=["pdf", "docx", "txt"], label_visibility="collapsed"
    )

with col2:
    st.subheader("💼 Job Description")
    jd_text = st.text_area(
        "Paste the job description here", height=220, label_visibility="collapsed",
        placeholder="Paste the full job description text here...",
    )

analyze_clicked = st.button("🔍 Analyze Match", type="primary", use_container_width=True)

# ---------------------------------------------------------------- results
if analyze_clicked:
    if resume_file is None or not jd_text.strip():
        st.warning("Please upload a resume AND paste a job description.")
    else:
        suffix = os.path.splitext(resume_file.name)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(resume_file.read())
            tmp_path = tmp.name

        with st.spinner("Reading resume and comparing with the job description..."):
            resume_text = extract_text(tmp_path)
            result = match(resume_text, jd_text, semantic_weight=semantic_weight, skill_weight=skill_weight)

        os.remove(tmp_path)

        st.divider()
        st.subheader("Overall Match")
        render_score_bar(result["overall_score"])
        st.write(verdict_text(result["overall_score"]))

        st.write("")  # small spacer
        m1, m2 = st.columns(2)
        m1.metric("Semantic similarity", f"{result['semantic_score']}%")
        m2.metric("Skill overlap", f"{result['skill_score']}%")

        st.write("")
        tab_matched, tab_missing, tab_extra = st.tabs(
            [
                f"✅ Matched ({len(result['matched_skills'])})",
                f"❌ Missing ({len(result['missing_skills'])})",
                f"➕ Extra ({len(result['extra_skills'])})",
            ]
        )

        with tab_matched:
            st.markdown(render_chips(result["matched_skills"], "chip-matched"), unsafe_allow_html=True)

        with tab_missing:
            st.markdown(render_chips(result["missing_skills"], "chip-missing"), unsafe_allow_html=True)
            if result["missing_skills"]:
                st.caption("Consider adding these skills to your resume if you genuinely have them.")

        with tab_extra:
            st.markdown(render_chips(result["extra_skills"], "chip-extra"), unsafe_allow_html=True)

        # ---- downloadable report
        report_lines = [
            "SkillSync — Match Report",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            f"Overall Match: {result['overall_score']}%",
            f"Semantic Similarity: {result['semantic_score']}%",
            f"Skill Overlap: {result['skill_score']}%",
            "",
            "Matched Skills: " + (", ".join(result["matched_skills"]) or "None"),
            "Missing Skills: " + (", ".join(result["missing_skills"]) or "None"),
            "Extra Skills: " + (", ".join(result["extra_skills"]) or "None"),
        ]
        st.download_button(
            "⬇️ Download report (.txt)",
            data="\n".join(report_lines),
            file_name="skillsync_match_report.txt",
            mime="text/plain",
            use_container_width=True,
        )