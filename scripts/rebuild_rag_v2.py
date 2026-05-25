#!/usr/bin/env python3
"""Inspect Rag_data taxonomy and chunk preview for rag_v2."""

from __future__ import annotations

import json
import sys
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.rag_v2.service import build_index_artifact, inspect_corpus, preview_answer, preview_chunks, preview_retrieval


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["taxonomy", "chunks", "build", "retrieve", "answer"], default="taxonomy")
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--question", type=str, default="")
    args = parser.parse_args()

    data_dir = PROJECT_ROOT / "Rag_data"
    if args.mode == "answer":
        if not args.question.strip():
            raise SystemExit("--question is required for --mode answer")
        items = preview_answer(args.question.strip())
    elif args.mode == "retrieve":
        if not args.question.strip():
            raise SystemExit("--question is required for --mode retrieve")
        items = preview_retrieval(args.question.strip(), top_k=max(1, args.limit))
    elif args.mode == "build":
        items = build_index_artifact(data_dir)
    elif args.mode == "chunks":
        items = preview_chunks(data_dir)[: max(1, args.limit)]
    else:
        items = inspect_corpus(data_dir)
    print(json.dumps(items, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
