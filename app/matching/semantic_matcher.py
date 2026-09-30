import numpy as np

from app.matching import embedder
from app.models import Evidence, JobPosting, Resume


def resume_chunks(resume: Resume) -> list[tuple[str, str]]:
    """(source label, text) pairs that job requirements are matched against."""
    chunks: list[tuple[str, str]] = []
    if resume.summary:
        chunks.append(("Summary", resume.summary))
    for s in resume.skills:
        chunks.append(("Skills", s))
    if resume.skills:
        chunks.append(("Skills", ", ".join(resume.skills)))
    for e in resume.experience:
        label = f"{e.title} @ {e.company}".strip(" @")
        for b in e.bullets:
            chunks.append((label, b))
    for ed in resume.education:
        text = " ".join(x for x in (ed.degree, ed.field, ed.institution) if x)
        if text:
            chunks.append(("Education", text))
    return chunks


def match_requirements(resume: Resume, job: JobPosting) -> list[Evidence]:
    reqs = job.requirements
    if not reqs:
        return []
    chunks = resume_chunks(resume)
    if not chunks:
        return [Evidence(requirement=r) for r in reqs]
    chunk_vecs = embedder.embed([c[1] for c in chunks])
    req_vecs = embedder.embed([r.text for r in reqs])
    sims = req_vecs @ chunk_vecs.T
    out = []
    for i, r in enumerate(reqs):
        j = int(np.argmax(sims[i]))
        out.append(
            Evidence(
                requirement=r,
                best_match_text=chunks[j][1],
                best_match_source=chunks[j][0],
                similarity=float(sims[i][j]),
            )
        )
    return out


def bullet_relevance(resume: Resume, job: JobPosting) -> dict[tuple[int, int], float]:
    """Max similarity of each experience bullet to any job requirement, keyed by (role_idx, bullet_idx)."""
    items = [(i, j, b) for i, e in enumerate(resume.experience) for j, b in enumerate(e.bullets)]
    if not items or not job.requirements:
        return {}
    b_vecs = embedder.embed([b for _, _, b in items])
    r_vecs = embedder.embed([r.text for r in job.requirements])
    sims = b_vecs @ r_vecs.T
    return {(i, j): float(sims[k].max()) for k, (i, j, _) in enumerate(items)}
