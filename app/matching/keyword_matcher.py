import re

from app.models import Evidence, JobPosting

ALIASES = {
    "javascript": ["js"],
    "typescript": ["ts"],
    "kubernetes": ["k8s"],
    "machine learning": ["ml"],
    "postgresql": ["postgres"],
    "amazon web services": ["aws"],
    "aws": ["amazon web services"],
    "node.js": ["nodejs"],
    "ci/cd": ["cicd", "ci-cd"],
    "continuous integration": ["ci"],
    "natural language processing": ["nlp"],
    "user experience": ["ux"],
}


def _variants(term: str) -> set[str]:
    t = term.lower().strip()
    return {t, *ALIASES.get(t, [])}


def contains_term(text: str, term: str) -> bool:
    """Whole-term, case-insensitive match that handles terms like C++, C#, Node.js."""
    if not term.strip():
        return False
    low = text.lower()
    for v in _variants(term):
        pattern = r"(?<![\w+#])" + re.escape(v) + r"(?:s|es)?(?![\w+#])"
        if re.search(pattern, low):
            return True
    return False


def apply_keyword_match(evidence: list[Evidence], resume_text: str) -> None:
    for ev in evidence:
        kws = ev.requirement.keywords
        ev.matched_keywords = [k for k in kws if contains_term(resume_text, k)]
        ev.missing_keywords = [k for k in kws if k not in ev.matched_keywords]


def job_keyword_coverage(resume_text: str, job: JobPosting) -> tuple[list[str], list[str]]:
    """ATS-style check: which posting keywords appear literally in the resume."""
    seen, found, missing = set(), [], []
    for k in job.keywords:
        if k.lower() in seen:
            continue
        seen.add(k.lower())
        (found if contains_term(resume_text, k) else missing).append(k)
    return found, missing