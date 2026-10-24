"""Heuristic v2: weight by rule; repeated occurrences add a capped penalty."""

from collections import defaultdict

WEIGHTS = {"critical": 10, "serious": 7, "moderate": 3, "minor": 1}
PRINCIPLES = ("perceivable", "operable", "understandable", "robust")


def calculate_score(issues: list[dict], pages_scanned: int = 1) -> int:
    groups = defaultdict(list)
    for i in issues:
        if i.get("category", "violation") == "violation":
            groups[i.get("rule_id", "unknown")].append(WEIGHTS.get(i.get("impact"), 1))
    penalty = sum(
        max(weights) * (1 + 0.25 * (min(len(weights), 5) - 1)) for weights in groups.values()
    )
    return max(0, round(100 - min(penalty / max(pages_scanned, 1), 100)))


def principle_scores(issues, pages_scanned=1):
    return {
        p: calculate_score([i for i in issues if i.get("principle") == p], pages_scanned)
        for p in PRINCIPLES
    }


def grade(score):
    if score >= 90:
        return "Low detected impact"
    if score >= 75:
        return "Some fixes needed"
    if score >= 50:
        return "Needs attention"
    return "High detected impact"
