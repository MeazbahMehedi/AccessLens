from app.services.scoring import calculate_score, principle_scores, grade

def test_no_issues_is_perfect():
    assert calculate_score([]) == 100

def test_weighted_penalty():
    assert calculate_score([{"impact":"serious"}]) == 93

def test_score_never_negative():
    assert calculate_score([{"impact":"critical"}] * 20) == 0

def test_principle_scores():
    scores = principle_scores([{"impact":"minor","principle":"operable"}])
    assert scores["operable"] == 99
    assert scores["perceivable"] == 100

def test_grade():
    assert grade(95) == "Excellent"
    assert grade(80) == "Good"
    assert grade(60) == "Needs work"
    assert grade(20) == "Poor"
