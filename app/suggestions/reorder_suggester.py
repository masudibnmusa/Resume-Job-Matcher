from typing import Optional

from app.matching import semantic_matcher
from app.models import JobPosting, ReorderSuggestion, Resume, ScoreBreakdown


def suggest_reorder(
    resume: Resume, job: JobPosting, score: Optional[ScoreBreakdown] = None
) -> list[ReorderSuggestion]:
    """Rule-based (no LLM): lead each role with its bullets most relevant to the posting."""
    out: list[ReorderSuggestion] = []

    if score and score.skills is not None and score.experience is not None and score.skills > score.experience + 15:
        out.append(
            ReorderSuggestion(
                role="Section order",
                note="Your skills line up better than your experience descriptions do. "
                "Consider placing a Skills section above Experience.",
            )
        )

    rel = semantic_matcher.bullet_relevance(resume, job)
    for i, e in enumerate(resume.experience):
        if len(e.bullets) < 3:
            continue
        order = sorted(range(len(e.bullets)), key=lambda j: -rel.get((i, j), 0.0))
        if order[0] != 0:
            label = f"{e.title} @ {e.company}".strip(" @")
            out.append(
                ReorderSuggestion(
                    role=label,
                    note="Lead with the bullets that best match this posting.",
                    lead_with=[e.bullets[j] for j in order[:2]],
                )
            )
    return out