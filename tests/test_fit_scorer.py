from app.matching import keyword_matcher, semantic_matcher
from app.models import Experience, JobPosting, Requirement, Resume
from app.scoring import fit_scorer, gap_analyzer

JOB = JobPosting(
    title="Backend Engineer",
    requirements=[
        Requirement(text="Experience with Python and Django", keywords=["Python", "Django"]),
        Requirement(text="Build REST APIs", keywords=["REST"]),
        Requirement(text="Experience with Kubernetes", keywords=["Kubernetes"], required=False),
    ],
    keywords=["Python", "Django", "REST", "Kubernetes"],
)


def _score(resume):
    ev = semantic_matcher.match_requirements(resume, JOB)
    keyword_matcher.apply_keyword_match(ev, resume.full_text())
    found, missing = keyword_matcher.job_keyword_coverage(resume.full_text(), JOB)
    fit_scorer.score_evidence(ev)
    return ev, fit_scorer.score_match(resume, JOB, ev, None, found, missing)


STRONG = Resume(
    skills=["Python", "Django", "REST"],
    experience=[Experience(title="Dev", company="A", bullets=["Built REST APIs with Python and Django"])],
)
WEAK = Resume(
    skills=["Photoshop"],
    experience=[Experience(title="Designer", company="B", bullets=["Designed posters"])],
)


def test_strong_beats_weak():
    _, strong = _score(STRONG)
    _, weak = _score(WEAK)
    assert strong.overall > weak.overall + 30


def test_required_weighs_more_than_preferred():
    ev, _ = _score(STRONG)
    ev[0].coverage, ev[2].coverage = 1.0, 0.0
    a = fit_scorer._weighted(ev)
    ev[0].coverage, ev[2].coverage = 0.0, 1.0
    b = fit_scorer._weighted(ev)
    assert a > b


def test_gaps_flag_missing_required():
    ev, score = _score(WEAK)
    gaps = gap_analyzer.analyze_gaps(ev, JOB, score, None, [])
    assert gaps and gaps[0].severity == "critical"
    assert any("Kubernetes" in g.requirement and g.severity == "minor" for g in gaps)