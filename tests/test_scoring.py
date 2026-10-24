from app.services.scoring import calculate_score, principle_scores, grade


def test_no_issues():
    assert calculate_score([]) == 100


def test_single_severity():
    assert calculate_score([{"rule_id": "label", "impact": "serious"}]) == 93


def test_repeated_rule_capped():
    assert calculate_score([{"rule_id": "label", "impact": "serious"}] * 100) == 86


def test_score_never_negative():
    assert calculate_score([{"rule_id": str(i), "impact": "critical"} for i in range(20)]) == 0


def test_review_excluded():
    assert (
        calculate_score(
            [
                {"rule_id": "test", "impact": "critical", "category": "review"},
                {"rule_id": "practice", "impact": "serious", "category": "best-practice"},
            ]
        )
        == 100
    )


def test_principles():
    scores = principle_scores([{"rule_id": "test", "impact": "minor", "principle": "operable"}])
    assert scores["operable"] == 99
    assert scores["perceivable"] == 100


def test_grade_describes_impact():
    assert grade(95) == "Low detected impact"
