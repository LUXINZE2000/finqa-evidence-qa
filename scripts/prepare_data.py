"""Download pinned FinQA splits and write selected sources, questions, and separate labels.

Inputs are upstream dev/test JSON and frozen IDs in eval/; outputs are data/processed,
data/labels, and the provenance manifest. This is optional for a normal checkout.
"""
import argparse
import hashlib
import random
import urllib.request
from src.data import ROOT, UPSTREAM_REV, read_json, write_json, source_document


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=6201)
    args = parser.parse_args()
    documents, manifest = {}, {"upstream_revision": UPSTREAM_REV, "seed": args.seed, "splits": {}}
    for split, count in [("dev", 10), ("test", 20)]:
        path = ROOT / "data" / "raw" / f"{split}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            url = f"https://raw.githubusercontent.com/czyssrs/FinQA/{UPSTREAM_REV}/dataset/{split}.json"
            with urllib.request.urlopen(url, timeout=60) as response:
                content = response.read()
            # Validate before saving a download.
            import json
            json.loads(content)
            path.write_bytes(content)
        records = read_json(path)
        id_path = ROOT / "eval" / f"{split}_ids.json"
        if id_path.exists():
            ids = read_json(id_path)
            if len(ids) != count or len(set(ids)) != count:
                raise ValueError(f"Expected exactly {count} unique {split} IDs")
        else:
            ids = random.Random(args.seed).sample(sorted(r["id"] for r in records), count)
            write_json(id_path, ids)
        by_id = {r["id"]: r for r in records}
        questions, labels = [], {}
        for cid in ids:
            record = by_id[cid]
            documents[cid] = source_document(record)
            questions.append({"id": cid, "question": record["qa"]["question"]})
            labels[cid] = {"exe_ans": record["qa"]["exe_ans"],
                           "answer": record["qa"].get("answer"),
                           "gold_ids": list(record["qa"]["gold_inds"])}
            chunk_ids = {c["id"] for c in documents[cid]["chunks"]}
            if not set(labels[cid]["gold_ids"]) <= chunk_ids:
                raise ValueError(f"Gold/source ID mismatch in {cid}")
        write_json(ROOT / "data" / "processed" / f"{split}_questions.json", questions)
        write_json(ROOT / "data" / "labels" / f"{split}.json", labels)
        manifest["splits"][split] = {"upstream_count": len(records), "selected_count": count,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "ids": ids}
    write_json(ROOT / "data" / "processed" / "documents.json", documents)
    write_json(ROOT / "eval" / "data_manifest.json", manifest)
    print("Prepared 10 development and 20 held-out test questions. Labels are separate from sources.")


if __name__ == "__main__":
    main()
