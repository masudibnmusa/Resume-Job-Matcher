from app.parsing.job_posting_parser import fallback_posting

POSTING = """Senior Python Developer
Acme Corp

Responsibilities:
- Design and build backend services

Requirements:
- 5+ years of experience with Python
- Strong knowledge of PostgreSQL

Nice to have:
- Experience with Kubernetes
"""


def test_fallback_posting():
    job = fallback_posting(POSTING)
    assert job.title == "Senior Python Developer"
    assert job.seniority == "senior"
    assert job.min_years == 5
    kinds = {r.text: (r.kind, r.required) for r in job.requirements}
    assert kinds["Design and build backend services"] == ("responsibility", True)
    assert kinds["Experience with Kubernetes"] == ("skill", False)
    assert "PostgreSQL" in job.keywords