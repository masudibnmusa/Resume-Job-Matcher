from app.utils.validators import check_rewrite

RESUME = "Built backend APIs in Python. Reduced page load time by 30%. Worked with Docker."


def test_accepts_faithful_rewrite():
    r = check_rewrite("Reduced page load time by 30%", "Cut page load time by 30%", RESUME)
    assert r.ok


def test_rejects_changed_number():
    r = check_rewrite("Reduced page load time by 30%", "Reduced page load time by 45%", RESUME)
    assert not r.ok


def test_rejects_unsupported_tool():
    r = check_rewrite("Worked with Docker", "Deployed services on Kubernetes", RESUME)
    assert not r.ok


def test_placeholders_allowed():
    r = check_rewrite("Worked with Docker", "Containerized services with Docker, [add metric]", RESUME)
    assert r.ok