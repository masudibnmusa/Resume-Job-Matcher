from app.models import Experience, JobPosting, Requirement, Resume
from app.suggestions.bullet_rewriter import rewrite_bullets, select_weak_bullets, weak_score

RESUME = Resume(
    experience=[Experience(title="Dev", company="Acme", bullets=["Responsible for backend APIs"])]
)
JOB = JobPosting(title="Backend", requirements=[Requirement(text="Build REST APIs in Python")])


class FakeLLM:
    def __init__(self, payload):
        self.payload = payload

    def complete_json(self, prompt, **kwargs):
        return self.payload


def test_weak_score_prefers_vague_bullets():
    assert weak_score("Responsible for backend APIs") > weak_score(
        "Reduced API latency by 40% across 12 services using caching"
    )


def test_select_weak_bullets():
    assert len(select_weak_bullets(RESUME, {}, limit=3)) == 1


def test_accepts_valid_rewrite():
    llm = FakeLLM({"rewrites": [{"id": 0, "rewritten": "Built backend APIs", "reason": "Stronger verb"}]})
    accepted, rejected = rewrite_bullets(RESUME, JOB, [], llm)
    assert len(accepted) == 1 and rejected == 0


def test_rejects_fabricated_rewrite():
    llm = FakeLLM({"rewrites": [{"id": 0, "rewritten": "Built backend APIs on Kubernetes serving 5M users"}]})
    accepted, rejected = rewrite_bullets(RESUME, JOB, [], llm)
    assert accepted == [] and rejected == 1