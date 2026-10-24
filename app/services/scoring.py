WEIGHTS = {"critical": 10, "serious": 7, "moderate": 3, "minor": 1}
PRINCIPLES = ("perceivable", "operable", "understandable", "robust")

def calculate_score(issues: list[dict], pages_scanned: int = 1) -> int:
    penalty = sum(WEIGHTS.get(i.get("impact", "minor"), 1) for i in issues)
    return max(0, round(100 - min(penalty / max(pages_scanned, 1), 100)))

def principle_scores(issues: list[dict], pages_scanned: int = 1) -> dict[str, int]:
    return {p: calculate_score([i for i in issues if i.get("principle") == p], pages_scanned) for p in PRINCIPLES}

def grade(score: int) -> str:
    if score >= 90: return "Excellent"
    if score >= 75: return "Good"
    if score >= 50: return "Needs work"
    return "Poor"
