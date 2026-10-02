"""BM25 and MiniLM retrieval; local dense and explicit OpenSearch backends."""
import hashlib
import math
import os
import re
from collections import Counter
from functools import lru_cache
from .data import ROOT, fingerprint


def tokens(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def bm25(question, chunks, k=3):
    if not chunks:
        return []
    counts = [Counter(tokens(c["text"])) for c in chunks]
    lengths = [sum(c.values()) for c in counts]
    avg = sum(lengths) / len(lengths) or 1
    query = set(tokens(question))
    df = {t: sum(t in c for c in counts) for t in query}
    scores = []
    for counts_i, length in zip(counts, lengths):
        score = 0.0
        for t in query:
            tf = counts_i[t]
            idf = math.log(1 + (len(chunks) - df[t] + .5) / (df[t] + .5))
            score += idf * tf * 2.5 / (tf + 1.5 * (.25 + .75 * length / avg))
        scores.append(score)
    order = sorted(range(len(chunks)), key=lambda i: (-scores[i], i))[:k]
    return [dict(chunks[i], score=scores[i]) for i in order]


@lru_cache(maxsize=1)
def encoder():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
                               cache_folder=str(ROOT / "data" / "cache" / "models"))


def embeddings(chunks):
    import numpy as np
    model_name = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    key = hashlib.sha256((model_name + fingerprint(chunks)).encode()).hexdigest()
    path = ROOT / "data" / "cache" / f"{key}.npy"
    if path.exists():
        return np.load(path, allow_pickle=False)
    values = encoder().encode([c["text"] for c in chunks], normalize_embeddings=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.save(path, values)
    return values


def dense(question, chunks, k=3):
    if not chunks:
        return []
    matrix = embeddings(chunks)
    query = encoder().encode(question, normalize_embeddings=True)
    scores = matrix @ query
    order = sorted(range(len(chunks)), key=lambda i: (-float(scores[i]), i))[:k]
    return [dict(chunks[i], score=float(scores[i])) for i in order]


def search_client():
    from opensearchpy import OpenSearch
    # Local development Compose binds to loopback. For hosted clusters use HTTPS.
    url = os.getenv("OPENSEARCH_URL", "http://localhost:9200")
    user, password = os.getenv("OPENSEARCH_USER"), os.getenv("OPENSEARCH_PASSWORD")
    return OpenSearch(hosts=[url], http_auth=(user, password) if user else None,
                      verify_certs=True, timeout=30)


def index_name(chunks):
    model = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    return "finqa-" + hashlib.sha256((model + fingerprint(chunks)).encode()).hexdigest()[:24]


def build_index(chunks):
    if not chunks:
        return None
    client, name = search_client(), index_name(chunks)
    if client.indices.exists(index=name):
        if client.count(index=name)["count"] != len(chunks):
            raise RuntimeError(f"Incomplete index {name}; remove it explicitly and rebuild")
        return name
    vectors = embeddings(chunks)
    client.indices.create(index=name, body={
        "settings": {"index.knn": True, "number_of_shards": 1, "number_of_replicas": 0},
        "mappings": {"properties": {
            "text": {"type": "text"}, "evidence_id": {"type": "keyword"},
            "vector": {"type": "knn_vector", "dimension": int(vectors.shape[1]),
                       "method": {"name": "hnsw", "engine": "lucene", "space_type": "cosinesimil"}}
        }}})
    from opensearchpy.helpers import bulk
    bulk(client, ({"_index": name, "_id": c["id"], "_source": {
        "evidence_id": c["id"], "text": c["text"], "vector": v.tolist()}}
                 for c, v in zip(chunks, vectors)))
    client.indices.refresh(index=name)
    return name


def opensearch_dense(question, chunks, k=3):
    if not chunks:
        return []
    name = index_name(chunks)
    client = search_client()
    if not client.indices.exists(index=name):
        raise RuntimeError("Index missing. Run python -m scripts.build_index first.")
    query = encoder().encode(question, normalize_embeddings=True).tolist()
    hits = client.search(index=name, body={"size": k, "query": {
        "knn": {"vector": {"vector": query, "k": k}}}})["hits"]["hits"]
    return [{"id": h["_source"]["evidence_id"], "text": h["_source"]["text"],
             "score": h["_score"]} for h in hits]


def retrieve(question, chunks, backend="local", k=3):
    # FinQA contains OCR fragments such as a lone word followed by punctuation.
    # They carry little independent meaning and can displace a complete table row.
    searchable = [c for c in chunks if c["id"].startswith("table_") or len(tokens(c["text"])) >= 3]
    if backend == "local":
        return dense(question, searchable, k)
    if backend == "opensearch":
        return opensearch_dense(question, searchable, k)
    if backend == "bm25":
        return bm25(question, searchable, k)
    raise ValueError(f"Unknown retrieval backend: {backend}")


def expand_context(chunks, hits):
    """Add original, separately citable neighbors without changing core ranking."""
    by_id = {c["id"]: c for c in chunks}
    table_ids = [c["id"] for c in chunks if c["id"].startswith("table_")]
    selected = {c["id"]: dict(c, role="core") for c in hits}
    added_by = {}
    for hit in hits:
        cid = hit["id"]
        if cid.startswith("table_"):
            ids = table_ids  # A single table row may need a distant comparison row.
        else:
            n = int(cid.split("_")[1])
            ids = [f"text_{n-1}", f"text_{n+1}"]
        for other in ids:
            if other in by_id and other not in selected:
                selected[other] = dict(by_id[other], role="context")
                added_by[other] = cid
    return list(selected.values()), added_by
