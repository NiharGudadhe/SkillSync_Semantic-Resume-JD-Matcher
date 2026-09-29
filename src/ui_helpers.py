"""
Tiny helpers that keep the Streamlit app working across Streamlit versions.

Newer Streamlit releases deprecate `use_container_width=True` in favour of
`width="stretch"`, but older releases (like the one on a laptop that was
installed months ago) only understand the old argument. This helper tries
the new form first and falls back to the old one, so the same app.py runs
on both your laptop and Streamlit Cloud.
"""


def stretch_call(widget, *args, **kwargs):
    """Calls a Streamlit widget so it fills the full container width."""
    try:
        return widget(*args, width="stretch", **kwargs)
    except Exception:  # older Streamlit: the argument is rejected before anything is drawn
        return widget(*args, use_container_width=True, **kwargs)