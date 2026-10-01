from app.matching.experience_level_matcher import total_years
from app.models import Experience, Resume
from app.parsing.resume_parser import extract_text
from app.parsing.section_extractor import parse_skills, rule_based_resume, split_sections

SAMPLE = """Jane Doe
jane@example.com

SUMMARY
Backend engineer.

SKILLS
Languages: Python, Go
Tools: Docker, PostgreSQL

EXPERIENCE
Senior Engineer at Acme Corp   Jan 2020 - Present
- Built REST APIs in Python
- Led a team of 4

Developer, Beta LLC  |  Jun 2016 - Dec 2019
- Wrote services

EDUCATION
BSc Computer Science, State University, 2016
"""


def test_split_sections():
    s = split_sections(SAMPLE)
    assert "Backend engineer" in s["summary"]
    assert "Docker" in s["skills"]


def test_parse_skills_strips_labels():
    skills = parse_skills("Languages: Python, Go\nTools: Docker")
    assert skills == ["Python", "Go", "Docker"]


def test_rule_based_resume():
    r = rule_based_resume(SAMPLE)
    assert r.name == "Jane Doe"
    assert len(r.experience) == 2
    assert r.experience[0].company == "Acme Corp"
    assert r.experience[0].bullets[0].startswith("Built REST APIs")
    assert r.experience[1].title == "Developer"
    assert r.education and "BSc" in r.education[0].degree


def test_total_years_merges_overlap():
    r = Resume(experience=[
        Experience(start="Jan 2018", end="Dec 2019"),
        Experience(start="Jun 2019", end="Dec 2019"),
    ])
    assert abs(total_years(r) - 2.0) < 0.01


def test_extract_text_txt(tmp_path):
    p = tmp_path / "r.txt"
    p.write_text("hello resume")
    assert extract_text(p) == "hello resume"