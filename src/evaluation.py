"""Project scoring policy, not the official FinQA leaderboard evaluator."""
import statistics
from decimal import Decimal
from .calculator import number


def correct(result, label):
    if result.get("status") != "answer":
        return False
    try:
        predicted = number(result["value"])
        # FinQA exe_ans expresses percentage answers as ratios. No automatic
        # x100 matching: only the declared percent kind triggers conversion.
        if result["kind"] == "percent":
            predicted /= 100
        target = number(label["exe_ans"])
        return abs(predicted - target) <= max(Decimal("0.0001"), abs(target) * Decimal("0.0001"))
    except (ValueError, KeyError):
        return False


def annotate(result, label):
    gold = set(label["gold_ids"])
    retrieved = {c["id"] for c in result.get("evidence", [])}
    cited = set(result.get("citations", []))
    return dict(result, correct=None if result["mode"] == "keyword" else correct(result, label),
                gold_ids=sorted(gold), gold_answer=label["exe_ans"],
                evidence_recall=len(gold & retrieved) / len(gold) if gold else None,
                all_gold_retrieved=gold <= retrieved if gold else None,
                core_gold_coverage=(len(gold & set(result.get("core_evidence_ids", []))) / len(gold)
                                    if gold and "core_evidence_ids" in result else None),
                citation_gold_overlap=len(cited & gold) / len(cited) if cited else None,
                manual_citation_supported="", manual_notes="")


def summarize(rows):
    if not rows:
        return {"n": 0}
    judged = [r for r in rows if r.get("correct") is not None]
    recalls = [r["evidence_recall"] for r in rows if r.get("evidence_recall") is not None]
    costs = [r.get("cost_usd") for r in rows]
    return {"n": len(rows), "accuracy": sum(r["correct"] for r in judged) / len(judged) if judged else None,
            "abstention_rate": sum(r["status"] == "abstain" for r in rows) / len(rows),
            "errors": sum(r["status"] in {"error", "invalid_output"} for r in rows),
            "mean_evidence_recall": statistics.mean(recalls) if recalls else None,
            "median_latency_seconds": statistics.median(r["latency_seconds"] for r in rows),
            "within_30_seconds_rate": sum(r["latency_seconds"] <= 30 for r in rows) / len(rows),
            "known_cost_usd": sum(c for c in costs if c is not None),
            "cost_missing_rows": sum(c is None for c in costs)}
