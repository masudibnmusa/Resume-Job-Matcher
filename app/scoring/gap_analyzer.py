from typing import Optional

from app import config
from app.models import Evidence, Gap, JobPosting, ScoreBreakdown

_SEV_ORDER = {"critical": 0, "moderate": 1, "minor": 2}


def _short(text: str, n: int = 100) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1] + "…"


def analyze_gaps(
    evidence: list[Evidence],
    job: JobPosting,
    score: ScoreBreakdown,
    level_score: Optional[float],
    level_notes: list[str],
) -> list[Gap]:
    found: list[tuple[float, Gap]] = []

    for ev in evidence:
        req = ev.requirement
        if req.kind == "education" or ev.coverage >= config.WEAK_THRESHOLD:
            continue
        status = "missing" if ev.coverage < config.MISSING_THRESHOLD else "weak"
        if not req.required:
            severity = "minor"
        elif status == "missing":
            severity = "critical"
        else:
            severity = "moderate"

        if status == "missing":
            reason = "Nothing in your resume clearly addresses this."
        else:
            reason = (
                f'Closest resume line is only a partial match: "{_short(ev.best_match_text)}" '
                f"({ev.best_match_source})."
            )
        if ev.missing_keywords:
            reason += f" Terms not found: {', '.join(ev.missing_keywords)}."

        found.append(
            (
                ev.coverage,
                Gap(
                    requirement=req.text,
                    required=req.required,
                    status=status,
                    severity=severity,
                    reason=reason,
                    missing_keywords=list(ev.missing_keywords),
                ),
            )
        )

    if level_score is not None and level_score < 0.8:
        found.append(
            (
                level_score,
                Gap(
                    requirement="Experience level / seniority",
                    status="weak",
                    severity="moderate",
                    reason=" ".join(level_notes) or "Level appears below what the posting asks for.",
                ),
            )
        )

    if job.education_required and score.education is not None and score.education < 100:
        found.append(
            (
                score.education / 100,
                Gap(
                    requirement=f"Education: {job.education_required}",
                    status="weak",
                    severity="moderate",
                    reason="Your listed education may be below the level requested.",
                ),
            )
        )

    found.sort(key=lambda t: (_SEV_ORDER[t[1].severity], t[0]))
    return [g for _, g in found]