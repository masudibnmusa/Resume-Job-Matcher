from typing import Optional

from app import config
from app.models import Evidence, JobPosting, Resume, ScoreBreakdown

DEGREE_RANKS = [
    ("phd", 4), ("ph.d", 4), ("doctor", 4),
    ("master", 3), ("msc", 3), ("m.s", 3), ("mba", 3),
    ("bachelor", 2), ("bsc", 2), ("b.s", 2), ("b.a", 2),
    ("associate", 1), ("diploma", 1),
]


def _norm_sim(sim: float) -> float:
    lo, hi = config.SIM_LOW, config.SIM_HIGH
    return min(1.0, max(0.0, (sim - lo) / (hi - lo)))


def requirement_coverage(ev: Evidence) -> float:
    sem = _norm_sim(ev.similarity)
    kws = ev.requirement.keywords
    if not kws:
        return sem
    kw = len(ev.matched_keywords) / len(kws)
    cov = config.SEMANTIC_WEIGHT * sem + config.KEYWORD_WEIGHT * kw
    if ev.requirement.kind == "skill" and kw == 1.0:
        cov = max(cov, config.KEYWORD_FLOOR)
    return cov


def score_evidence(evidence: list[Evidence]) -> None:
    for ev in evidence:
        ev.coverage = requirement_coverage(ev)


def _weighted(evs: list[Evidence]) -> Optional[float]:
    if not evs:
        return None
    ws = [config.REQUIRED_WEIGHT if e.requirement.required else config.PREFERRED_WEIGHT for e in evs]
    return sum(e.coverage * w for e, w in zip(evs, ws)) / sum(ws)


def _degree_rank(text: str) -> int:
    low = text.lower()
    return max((rank for key, rank in DEGREE_RANKS if key in low), default=0)


def education_score(resume: Resume, job: JobPosting) -> Optional[float]:
    if not job.education_required:
        return None
    need = _degree_rank(job.education_required)
    have = max((_degree_rank(f"{e.degree} {e.field}") for e in resume.education), default=0)
    if need == 0:
        return 1.0 if have > 0 else 0.5
    return min(1.0, have / need)


def _pct(x: Optional[float]) -> Optional[float]:
    return None if x is None else round(x * 100, 1)


def score_match(
    resume: Resume,
    job: JobPosting,
    evidence: list[Evidence],
    level_score: Optional[float],
    kw_found: list[str],
    kw_missing: list[str],
) -> ScoreBreakdown:
    skills = _weighted([e for e in evidence if e.requirement.kind == "skill"])
    resp = _weighted([e for e in evidence if e.requirement.kind in ("responsibility", "experience")])
    exp_parts = [x for x in (resp, level_score) if x is not None]
    experience = sum(exp_parts) / len(exp_parts) if exp_parts else None
    education = education_score(resume, job)

    cats = {"skills": skills, "experience": experience, "education": education}
    used = {k: v for k, v in cats.items() if v is not None}
    total_w = sum(config.CATEGORY_WEIGHTS[k] for k in used)
    overall = sum(config.CATEGORY_WEIGHTS[k] * v for k, v in used.items()) / total_w if total_w else 0.0

    kw_total = len(kw_found) + len(kw_missing)
    semantic_signal = sum(_norm_sim(e.similarity) for e in evidence) / len(evidence) if evidence else 0.0

    return ScoreBreakdown(
        overall=_pct(overall) or 0.0,
        skills=_pct(skills),
        experience=_pct(experience),
        education=_pct(education),
        semantic_signal=_pct(semantic_signal) or 0.0,
        keyword_signal=_pct(len(kw_found) / kw_total) if kw_total else None,
        level_signal=_pct(level_score),
    )