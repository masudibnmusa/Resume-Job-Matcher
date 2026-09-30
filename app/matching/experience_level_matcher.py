import re
from datetime import date
from typing import Optional

from app.models import JobPosting, Resume

MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}
PRESENT = ("present", "current", "now", "ongoing", "today")

SENIORITY_RANK = {
    "intern": 0, "junior": 1, "jr": 1, "entry": 1, "associate": 1,
    "mid": 2, "intermediate": 2,
    "senior": 3, "sr": 3,
    "lead": 4, "staff": 4, "manager": 4,
    "principal": 5, "director": 6, "head": 6, "vp": 7,
}


def _parse_ym(s: str, is_end: bool) -> Optional[int]:
    """Return a month index (year*12+month), or None if unparseable."""
    s = s.strip().lower()
    if not s:
        return None
    if any(p in s for p in PRESENT):
        t = date.today()
        return t.year * 12 + t.month
    m = re.search(r"([a-z]{3})[a-z]*\.?\s+((?:19|20)\d{2})", s)
    if m and m.group(1) in MONTHS:
        return int(m.group(2)) * 12 + MONTHS[m.group(1)]
    m = re.search(r"\b(\d{1,2})[/-]((?:19|20)\d{2})\b", s)
    if m and 1 <= int(m.group(1)) <= 12:
        return int(m.group(2)) * 12 + int(m.group(1))
    m = re.search(r"\b((?:19|20)\d{2})\b", s)
    if m:
        return int(m.group(1)) * 12 + (12 if is_end else 1)
    return None


def total_years(resume: Resume) -> float:
    """Total years of experience with overlapping roles merged.

    Note: this is overall experience only. Years *per skill* is not estimated,
    because attributing skills to date ranges is unreliable.
    """
    intervals = []
    for e in resume.experience:
        a = _parse_ym(e.start, False)
        b = _parse_ym(e.end or "present", True)
        if a is None or b is None or b < a:
            continue
        intervals.append([a, b])
    intervals.sort()
    merged: list[list[int]] = []
    for a, b in intervals:
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return sum(b - a + 1 for a, b in merged) / 12


def rank_from_text(text: str) -> Optional[int]:
    tokens = re.findall(r"[a-z]+", text.lower())
    ranks = [SENIORITY_RANK[t] for t in tokens if t in SENIORITY_RANK]
    return max(ranks) if ranks else None


def _resume_rank(resume: Resume, years: float) -> int:
    ranks = [r for r in (rank_from_text(e.title) for e in resume.experience) if r is not None]
    if ranks:
        return max(ranks)
    if years < 2:
        return 1
    if years < 5:
        return 2
    if years < 8:
        return 3
    return 4


def level_match(resume: Resume, job: JobPosting) -> tuple[Optional[float], list[str]]:
    """Return (score 0..1 or None if nothing to compare, human-readable notes)."""
    notes: list[str] = []
    scores: list[float] = []
    have = total_years(resume)

    if job.min_years:
        if have > 0:
            scores.append(min(1.0, have / job.min_years))
            notes.append(f"Posting asks for {job.min_years:g}+ years; your resume shows about {have:.1f}.")
        else:
            notes.append("Could not read employment dates, so years of experience were not scored.")

    job_rank = rank_from_text(job.seniority or job.title)
    if job_rank is not None:
        diff = job_rank - _resume_rank(resume, have)
        scores.append(1.0 if diff <= 0 else max(0.0, 1 - 0.3 * diff))
        if diff > 0:
            notes.append("The role's seniority is above the level your titles and years suggest.")

    return (sum(scores) / len(scores) if scores else None), notes