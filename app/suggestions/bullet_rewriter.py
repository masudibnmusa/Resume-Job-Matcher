import re

from app.llm.llm_client import LLMClient
from app.matching import semantic_matcher
from app.models import BulletSuggestion, Gap, JobPosting, Resume
from app.suggestions.prompt_templates import SYSTEM_TRUTHFUL, bullet_rewrite_prompt
from app.utils import validators

WEAK_STARTS = (
    "responsible for", "worked on", "helped", "assisted", "involved in", "duties included", "tasked with",
)


def weak_score(text: str) -> int:
    t = text.strip().lower()
    score = 0
    if t.startswith(WEAK_STARTS):
        score += 2
    if not re.search(r"\d", t):
        score += 1
    if len(t.split()) < 8:
        score += 1
    return score


def select_weak_bullets(
    resume: Resume, relevance: dict[tuple[int, int], float], limit: int = 5
) -> list[tuple[float, int, int, str, str]]:
    cands = []
    for i, e in enumerate(resume.experience):
        label = f"{e.title} @ {e.company}".strip(" @")
        for j, b in enumerate(e.bullets):
            rel = relevance.get((i, j), 0.0)
            priority = weak_score(b) + (1 - min(1.0, rel / 0.65))
            cands.append((priority, i, j, label, b))
    cands.sort(key=lambda x: -x[0])
    return cands[:limit]


def rewrite_bullets(
    resume: Resume, job: JobPosting, gaps: list[Gap], llm: LLMClient, limit: int = 5
) -> tuple[list[BulletSuggestion], int]:
    """Return (validated suggestions, number of rewrites rejected by the validator)."""
    relevance = semantic_matcher.bullet_relevance(resume, job)
    candidates = select_weak_bullets(resume, relevance, limit)
    if not candidates:
        return [], 0

    payload = [{"id": k, "role": c[3], "bullet": c[4]} for k, c in enumerate(candidates)]
    focus_terms = []
    for g in gaps:
        focus_terms.extend(g.missing_keywords)
    focus_terms = list(dict.fromkeys(focus_terms))[:15]

    data = llm.complete_json(
        bullet_rewrite_prompt(job.title, [r.text for r in job.requirements][:15], payload, focus_terms),
        system=SYSTEM_TRUTHFUL,
    )
    items = data.get("rewrites", []) if isinstance(data, dict) else []

    resume_text = resume.full_text()
    accepted: list[BulletSuggestion] = []
    rejected = 0
    for item in items:
        try:
            cand = candidates[int(item["id"])]
            rewritten = str(item["rewritten"]).strip()
        except (KeyError, ValueError, IndexError, TypeError):
            continue
        original = cand[4]
        if not rewritten or rewritten == original:
            continue
        result = validators.check_rewrite(original, rewritten, resume_text)
        if not result.ok:
            rejected += 1
            continue
        accepted.append(
            BulletSuggestion(role=cand[3], original=original, rewritten=rewritten, reason=str(item.get("reason", "")))
        )
    return accepted, rejected