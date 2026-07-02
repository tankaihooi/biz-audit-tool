"""Streamlit frontend. Sends a workflow string, renders a Recommendation.

Keep this dumb: no model logic here, just I/O and display.
"""

import os

import requests
import streamlit as st

try:
    BACKEND_URL = st.secrets["BACKEND_URL"]
except Exception:
    # No secrets.toml locally (only present on Streamlit Community Cloud)
    BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Business Process Audit Tool", page_icon="🔍")
st.title("Business Process Audit Tool")
st.caption("Describe a business workflow. Get bottlenecks, AI fixes, and ROI estimates.")

workflow = st.text_area(
    "Describe your workflow",
    height=180,
    placeholder="e.g. Orders arrive by email. Staff re-type them into our ERP, "
    "then manually check stock and reply to the customer...",
)

if st.button("Audit workflow", type="primary"):
    text = workflow.strip()
    if not text:
        st.warning("Please describe a workflow first.")
        st.stop()

    try:
        resp = requests.post(
            f"{BACKEND_URL}/recommend",
            json={"workflow_description": text},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        st.error(f"Backend error: {e}")
        st.stop()

    st.subheader("Summary")
    st.write(data["summary"])

    st.subheader("Bottlenecks & recommendations")
    for i, b in enumerate(data["bottlenecks"], 1):
        with st.expander(f"{i}. {b['description']}", expanded=True):
            st.markdown(f"**AI tools:** {', '.join(b['ai_tools'])}")
            col1, col2 = st.columns(2)
            col1.metric("Est. time saved", b["estimated_time_saved"])
            col2.metric("Implementation", b["implementation_difficulty"])
