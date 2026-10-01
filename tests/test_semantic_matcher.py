from app.matching.semantic_matcher import bullet_relevance, match_requirements
from app.models import Experience, JobPosting, Requirement, Resume


def _resume():
    return Resume(
        skills=["Python", "Docker"],
        experience=[Experience(title="Dev", company="Acme", bullets=["Built REST APIs in Python", "Organized team lunches"])],
    )


def _job():
    return JobPosting(requirements=[Requirement(text="Build REST APIs in Python")])


def test_match_finds_best_line():
    ev = match_requirements(_resume(), _job())[0]
    assert "REST APIs" in ev.best_match_text
    assert ev.similarity > 0.5


def test_bullet_relevance_ranks_relevant_higher():
    rel = bullet_relevance(_resume(), _job())
    assert rel[(0, 0)] > rel[(0, 1)]