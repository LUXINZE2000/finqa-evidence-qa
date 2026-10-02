"""Streamlit demo for one FinQA excerpt; reads prepared sources and calls the QA pipeline.

The UI exposes development examples only. Gold labels are not loaded here.
"""
import os
import streamlit as st
from dotenv import load_dotenv
from src.data import ROOT, load_cases, load_document
from src.pipeline import answer

load_dotenv(ROOT / ".env")
st.set_page_config(page_title="FinQA Evidence QA", page_icon="📊", layout="wide")
st.title("FinQA Evidence QA")
st.caption("Financial report excerpts · cited evidence · verifiable arithmetic")
st.info("Research prototype for checking report excerpts. Review source evidence before using an answer.")
if not (ROOT / "data" / "processed" / "documents.json").exists():
    st.warning("First run: python -m scripts.prepare_data")
    st.stop()
cases = load_cases("dev")
case = st.selectbox("Choose a development report excerpt", cases, format_func=lambda c: c["id"])
question = st.text_area("Question", value=case["question"], key=case["id"])
mode_label = st.radio("Method", ["RAG", "Full context", "Keyword evidence only"], horizontal=True)
mode = {"RAG": "rag", "Full context": "full", "Keyword evidence only": "keyword"}[mode_label]
with st.sidebar:
    st.header("Configuration")
    backend = st.selectbox("Dense retrieval backend", ["local", "opensearch"])
    st.write("Model:", os.getenv("OPENROUTER_MODEL", "Not configured"))
    st.caption("API keys stay in your local .env file. The interface exposes development examples only.")
if st.button("Find answer", type="primary", disabled=not question.strip()):
    with st.spinner("Retrieving evidence and checking the answer…"):
        result = answer(question, load_document(case["id"]), mode, backend)
    if result["status"] == "answer":
        if result["kind"] == "percent" and float(result["value"]) < 0:
            st.success(f"Answer: decrease of {abs(float(result['value'])):.4g}% (signed change: {result['value']}%)")
        else:
            suffix = "%" if result["kind"] == "percent" else result["unit"]
            st.success(f"Answer: {result['value']} {suffix}")
        st.write("Citations:", ", ".join(result["citations"]))
        st.subheader("Calculation")
        for i, operand in enumerate(result["operands"]):
            st.write(f"n{i} = {operand['value']} [{operand['evidence_id']}]")
        for i, step in enumerate(result["steps"]):
            st.code(f"s{i} = {step['op']}({', '.join(step['args'])})")
    elif result["status"] == "abstain":
        st.warning("I don't know: " + result["reason"])
    elif result["status"] != "retrieval_only":
        st.error(result.get("reason", "Answer could not be validated"))
    st.caption(f"Elapsed: {result['latency_seconds']:.2f}s · Reported cost: " +
               (f"${result['cost_usd']:.6f}" if result.get("cost_usd") is not None else "unavailable"))
    st.subheader("Source evidence")
    for chunk in result.get("evidence", []):
        with st.expander(chunk["id"], expanded=True):
            st.text(chunk["text"])
