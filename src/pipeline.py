"""Orchestrate evidence retrieval, one model call, guarded arithmetic, and abstention.

This module receives a source document and question only; scoring labels stay in the evaluator.
"""
import time
from .calculator import validate_and_calculate
from .model import generate
from .retrieval import expand_context, retrieve


def answer(question, document, mode="rag", backend="local", generator=generate):
    start = time.perf_counter()
    result = {"case_id": document["id"], "mode": mode, "backend": backend,
              "question": question}
    try:
        if mode not in {"rag", "full", "keyword"}:
            raise ValueError("Unknown mode")
        if mode == "full":
            evidence = document["chunks"]
        else:
            core = retrieve(question, document["chunks"], "bm25" if mode == "keyword" else backend,
                            k=3 if mode == "keyword" else 5)
            if mode == "rag":
                evidence, added_by = expand_context(document["chunks"], core)
                result["core_evidence_ids"] = [c["id"] for c in core]
                result["context_added_by"] = added_by
            else:
                evidence = core
        result["evidence"] = evidence
        result["retrieval_seconds"] = time.perf_counter() - start
        if mode == "keyword":
            result["status"] = "retrieval_only"
        elif not evidence:
            result.update(status="abstain", reason="No evidence available", cost_usd=0)
        else:
            payload, meta = generator(question, [{"id": c["id"], "text": c["text"]} for c in evidence])
            result.update(meta)
            result["model_output"] = payload
            if payload.get("status") == "invalid_output":
                result.update(status="invalid_output", reason=payload.get("parse_error", "invalid model response"))
                return dict(result, latency_seconds=time.perf_counter() - start)
            try:
                result.update(validate_and_calculate(payload, evidence))
            except (ValueError, KeyError, TypeError, ArithmeticError) as exc:
                result.update(status="invalid_output", reason=str(exc))
    except Exception as exc:
        result.update(status="error", reason=str(exc))
    result["latency_seconds"] = time.perf_counter() - start
    return result
