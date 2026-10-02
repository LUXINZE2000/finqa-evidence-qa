"""Warm the local embedding cache or optional OpenSearch index for selected cases.

Reads prepared source chunks; does not read answer labels or call the answer model.
"""
import argparse
from dotenv import load_dotenv
from src.data import ROOT, load_cases, load_document
from src.retrieval import build_index, embeddings


def main():
    load_dotenv(ROOT / ".env")
    p = argparse.ArgumentParser()
    p.add_argument("--backend", choices=["local", "opensearch"], default="local")
    p.add_argument("--split", choices=["dev", "test", "all"], default="dev")
    args = p.parse_args()
    splits = ["dev", "test"] if args.split == "all" else [args.split]
    for split in splits:
        for case in load_cases(split):
            chunks = load_document(case["id"])["chunks"]
            if args.backend == "opensearch":
                build_index(chunks)
            else:
                embeddings(chunks)
            print("Indexed", case["id"])


if __name__ == "__main__":
    main()
