from collections import defaultdict
from typing import Any

import numpy as np


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    va = np.asarray(a, dtype=np.float32)
    vb = np.asarray(b, dtype=np.float32)
    denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
    if denom <= 1e-12:
        return 0.0
    return float(np.dot(va, vb) / denom)


def find_best_match(
    query_embedding: np.ndarray,
    candidates: list[dict[str, Any]],
    threshold: float = 0.40,
) -> dict[str, Any]:
    best_by_visitor: dict[int, dict[str, Any]] = defaultdict(dict)

    for candidate in candidates:
        score = cosine_similarity(query_embedding, candidate["embedding"])
        visitor_id = int(candidate["visitor_id"])
        current = best_by_visitor.get(visitor_id)
        enriched = {**candidate, "score": score}
        if not current or score > current.get("score", -1.0):
            best_by_visitor[visitor_id] = enriched

    all_best = sorted(best_by_visitor.values(), key=lambda item: item["score"], reverse=True)
    best = all_best[0] if all_best else None

    return {
        "matched": bool(best and best["score"] >= threshold),
        "best": best,
        "top_matches": all_best[:5],
        "threshold": threshold,
    }
