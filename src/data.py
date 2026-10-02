"""Only allowlisted source fields may enter the retrieval corpus."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_REV = "0f16e2867befa6840783e58be38c9efb9229d742"


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def chunks_from_record(record):
    """Preserve FinQA text_N/table_N identifiers, including original row indices."""
    chunks = []
    texts = record.get("pre_text", []) + record.get("post_text", [])
    for i, text in enumerate(texts):
        if any(c.isalnum() for c in text):
            chunks.append({"id": f"text_{i}", "text": text})
    table = record.get("table", [])
    if table:
        headers = table[0]
        for i, row in enumerate(table):
            if i == 0:
                text = "Table headers: " + " | ".join(row)
            else:
                cells = [f"{headers[j] if j < len(headers) else 'column ' + str(j)}: {value}"
                         for j, value in enumerate(row)]
                text = "Table row: " + " | ".join(cells)
            chunks.append({"id": f"table_{i}", "text": text})
    return chunks


def source_document(record):
    # Never copy qa, model_input, gold_inds, program or retrieved fields here.
    return {"id": record["id"], "source": record.get("filename", record["id"]),
            "chunks": chunks_from_record(record)}


def fingerprint(chunks):
    return hashlib.sha256(json.dumps(chunks, sort_keys=True).encode()).hexdigest()


def load_cases(split="dev"):
    return read_json(ROOT / "data" / "processed" / f"{split}_questions.json")


def load_document(case_id):
    documents = read_json(ROOT / "data" / "processed" / "documents.json")
    return documents[case_id]
