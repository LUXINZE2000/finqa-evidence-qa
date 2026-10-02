"""Export descriptive metrics and an honest, reviewable experiment report."""
import argparse
import csv
import json
import statistics
from pathlib import Path
from src.data import ROOT, write_json


def wilson(successes, n):
    z = 1.959963984540054
    p = successes / n
    center = (p + z*z/(2*n)) / (1+z*z/n)
    half = z*((p*(1-p)/n+z*z/(4*n*n))**.5)/(1+z*z/n)
    return [center-half, center+half]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("run", help="Run directory, relative to repository or absolute")
    args = p.parse_args()
    run = Path(args.run)
    if not run.is_absolute():
        run = ROOT / run
    metadata = json.loads((run / "run.json").read_text(encoding="utf-8"))
    metrics, all_rows = {}, []
    for mode in metadata["modes"]:
        rows = [json.loads(line) for line in (run / f"{mode}.jsonl").read_text(encoding="utf-8").splitlines()]
        if len(rows) != len(metadata["cases"]):
            raise ValueError(f"Incomplete {mode} run: {len(rows)} rows")
        n = len(rows)
        known_costs = [r["cost_usd"] for r in rows if r.get("cost_usd") is not None]
        latencies = sorted(r["latency_seconds"] for r in rows)
        token_rows = [r for r in rows if "usage" in r]
        recalls = [r["evidence_recall"] for r in rows if r.get("evidence_recall") is not None]
        successes = sum(r.get("correct") is True for r in rows)
        m = {"n": n, "correct": successes if mode != "keyword" else None,
             "accuracy": successes/n if mode != "keyword" else None,
             "accuracy_wilson_95_interval": wilson(successes, n) if mode != "keyword" else None,
             "answers": sum(r["status"] == "answer" for r in rows),
             "abstentions": sum(r["status"] == "abstain" for r in rows),
             "invalid_outputs": sum(r["status"] == "invalid_output" for r in rows),
             "api_or_runtime_errors": sum(r["status"] == "error" for r in rows),
             "mean_evidence_recall": statistics.mean(recalls) if recalls else None,
             "all_gold_retrieved_count": sum(r.get("all_gold_retrieved") is True for r in rows),
             "latency_median_seconds": statistics.median(latencies),
             "latency_mean_seconds": statistics.mean(latencies),
             "latency_min_seconds": min(latencies), "latency_max_seconds": max(latencies),
             "within_30_seconds_count": sum(t <= 30 for t in latencies),
             "prompt_tokens": sum(r["usage"].get("prompt_tokens", 0) for r in token_rows),
             "completion_tokens": sum(r["usage"].get("completion_tokens", 0) for r in token_rows),
             "reasoning_tokens": sum((r["usage"].get("completion_tokens_details") or {}).get("reasoning_tokens", 0) for r in token_rows),
             "usage_missing_rows": n-len(token_rows) if mode != "keyword" else 0,
             "reported_cost_usd": sum(known_costs) if mode != "keyword" else 0,
             "cost_missing_rows": n-len(known_costs) if mode != "keyword" else 0}
        metrics[mode] = m
        for r in rows:
            all_rows.append({"mode": mode, "case_id": r["case_id"], "question": r["question"],
                "status": r["status"], "prediction": r.get("value"), "kind": r.get("kind"),
                "unit": r.get("unit"), "reference": r.get("gold_answer"), "correct": r.get("correct"),
                "evidence_recall": r.get("evidence_recall"), "all_gold_retrieved": r.get("all_gold_retrieved"),
                "citations": ";".join(r.get("citations", [])),
                "latency_seconds": r["latency_seconds"],
                "prompt_tokens": r.get("usage", {}).get("prompt_tokens"),
                "completion_tokens": r.get("usage", {}).get("completion_tokens"),
                "cost_usd": r.get("cost_usd"), "error_or_abstention_reason": r.get("reason", ""),
                "manual_citation_supported": r.get("manual_citation_supported", ""),
                "manual_notes": r.get("manual_notes", "")})
    write_json(run / "metrics.json", metrics)
    with (run / "all_results.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(all_rows[0]))
        writer.writeheader()
        writer.writerows(all_rows)
    lines = ["# FinQA evaluation report", "", f"Split: {metadata['split']}; model: {metadata.get('model')}",
             f"Cases: {len(metadata['cases'])}; backend: {metadata['backend']}", "",
             "| Method | Correct | Mean evidence recall | Median seconds | <=30s | Reported cost USD |",
             "|---|---:|---:|---:|---:|---:|"]
    for mode, m in metrics.items():
        score = "N/A (retrieval only)" if m["accuracy"] is None else f"{m['correct']}/{m['n']} ({m['accuracy']:.0%})"
        lines.append(f"| {mode} | {score} | {m['mean_evidence_recall']:.1%} | {m['latency_median_seconds']:.3f} | {m['within_30_seconds_count']}/{m['n']} | {m['reported_cost_usd']:.6f} |")
    lines += ["", "## Interpretation limits", "",
              "- These are project numerical scores using the frozen policy, not official FinQA leaderboard scores.",
              "- All cases stay in the accuracy denominator, including errors and abstentions.",
              "- Gold-ID retrieval coverage is not semantic citation correctness. Manual citation/unit/formula review is pending unless explicitly completed.",
              "- Latency is measured after embedding setup; indexing, downloads and UI startup are excluded.",
              "- API costs are provider-reported. Local compute costs are excluded; missing costs remain missing in metrics.json.",
              "- Small-sample descriptive results do not establish general superiority. See Wilson intervals in metrics.json.",
              "- Empty-evidence guards are tested separately and do not demonstrate nuanced model abstention.",
              "", "## Incorrect / unsuccessful model cases", ""]
    for r in all_rows:
        if r["mode"] != "keyword" and r["correct"] is not True:
            lines.append(f"- {r['mode']} · {r['case_id']}: {r['status']}; predicted={r['prediction']} ({r['kind']}), reference={r['reference']}; {r['error_or_abstention_reason']}")
    (run / "report.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    print("Report:", run / "report.md")


if __name__ == "__main__":
    main()
