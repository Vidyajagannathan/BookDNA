"""Incremental, deterministic BookDNA scoring primitives."""
from dataclasses import dataclass

STATUS_WEIGHTS = {"WANT_TO_READ": 0.0, "CURRENTLY_READING": 0.15, "READ": 1.0, "DNF": 0.0}
RATING_WEIGHTS = {0.5:.05, 1:.10, 1.5:.20, 2:.35, 2.5:.60, 3:.85, 3.5:1, 4:1.15, 4.5:1.25, 5:1.35}

@dataclass(frozen=True)
class Signal:
    status: str
    rating: float | None = None
    favourite: bool = False

def contribution(signal: Signal, traits: dict[str, float]) -> dict[str, float]:
    status_weight = STATUS_WEIGHTS.get(signal.status, 0)
    rating_weight = RATING_WEIGHTS.get(signal.rating, 1.0) if signal.rating else 1.0
    favourite_weight = 1.25 if signal.favourite else 1.0
    multiplier = status_weight * rating_weight * favourite_weight
    return {trait: round(weight * multiplier, 6) for trait, weight in traits.items() if weight > 0 and multiplier > 0}

def display_score(evidence: float, total_evidence: float, prior: float = 1.8) -> float:
    if evidence <= 0 or total_evidence <= 0:
        return 0
    raw_affinity = evidence / total_evidence
    confidence = evidence / (evidence + prior)
    # Affinity is relative, confidence prevents one book from claiming certainty.
    return round(min(100, raw_affinity * confidence * 180), 1)

def similarity(left: dict[str, float], right: dict[str, float]) -> float:
    keys = set(left) | set(right)
    if not keys:
        return 0
    dot = sum(left.get(k, 0) * right.get(k, 0) for k in keys)
    a = sum(left.get(k, 0) ** 2 for k in keys) ** .5
    b = sum(right.get(k, 0) ** 2 for k in keys) ** .5
    return round(100 * dot / (a * b), 1) if a and b else 0

