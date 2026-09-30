from datetime import datetime

from app.models import MatchResult


def _bar(score: float | None, width: int = 20) -> str:
    if score is None:
        return "n/a"
    filled = round(score / 100 * width)
    return "█" * filled + "░" * (width - filled) + f" {score:.0f}/100"


def _cell(text: str, n: int = 90) -> str:
    text = " ".join(str(text).split()).replace("|", "\\|")
    return text if len(text) <= n else text[: n - 1] + "…"


def _status(cov: float) -> str:
    if cov >= 0.6:
        return "✅ Strong"
    if cov >= 0.25:
        return "⚠️ Weak"
    return "❌ Missing"


def build_report(r: MatchResult) -> str:
    s = r.score
    L: list[str] = []
    title = r.job.title or "Job posting"
    L.append(f"# Resume Match Report: {title}" + (f" at {r.job.company}" if r.job.company else ""))
    L.append("")
    L.append(f"**Candidate:** {r.resume.name or 'Unknown'}  ")
    L.append(f"**Generated:** {datetime.now():%Y-%m-%d %H:%M}")
    L.append("")

    L.append("## Overall fit")
    L.append("")
    L.append(f"**{s.overall:.0f} / 100**")
    L.append("")
    L.append("| Category | Score |")
    L.append("|---|---|")
    L.append(f"| Skills | {_bar(s.skills)} |")
    L.append(f"| Experience | {_bar(s.experience)} |")
    L.append(f"| Education | {_bar(s.education)} |")
    L.append("")
    L.append("Underlying signals: "
             f"semantic similarity {s.semantic_signal:.0f}/100, "
             f"keyword coverage {'n/a' if s.keyword_signal is None else f'{s.keyword_signal:.0f}/100'}, "
             f"experience level {'n/a' if s.level_signal is None else f'{s.level_signal:.0f}/100'}.")
    L.append("")
    L.append("> This score is a guide to where your resume is strong or thin, not a prediction of hiring outcomes.")
    L.append("")

    if r.warnings:
        L.append("## Notes")
        L.append("")
        for w in r.warnings:
            L.append(f"- {w}")
        L.append("")

    if r.gaps:
        L.append("## Gaps to address")
        L.append("")
        for sev, heading in (("critical", "Critical"), ("moderate", "Moderate"), ("minor", "Minor")):
            group = [g for g in r.gaps if g.severity == sev]
            if not group:
                continue
            L.append(f"### {heading}")
            L.append("")
            for g in group:
                tag = "required" if g.required else "preferred"
                L.append(f"- **{g.requirement}** ({tag}, {g.status}). {g.reason}")
            L.append("")

    L.append("## ATS keyword check")
    L.append("")
    L.append(f"- **Found ({len(r.keywords_found)}):** {', '.join(r.keywords_found) or 'none'}")
    L.append(f"- **Missing ({len(r.keywords_missing)}):** {', '.join(r.keywords_missing) or 'none'}")
    L.append("")

    if r.bullet_suggestions:
        L.append("## Suggested bullet rewrites")
        L.append("")
        L.append("Review each one. Keep only what is accurate, and fill in any `[add metric]` placeholders with real numbers.")
        L.append("")
        for b in r.bullet_suggestions:
            L.append(f"**{b.role}**")
            L.append(f"- Before: {b.original}")
            L.append(f"- After: {b.rewritten}")
            if b.reason:
                L.append(f"- Why: {b.reason}")
            L.append("")

    if r.keyword_suggestions:
        L.append("## Working in missing keywords (only if true)")
        L.append("")
        for k in r.keyword_suggestions:
            L.append(f"- **{k.term}** ({k.where or 'where it fits'}). {k.condition}")
            if k.example:
                L.append(f"  - Example: {k.example}")
        L.append("")

    if r.reorder_suggestions:
        L.append("## Reordering suggestions")
        L.append("")
        for o in r.reorder_suggestions:
            L.append(f"- **{o.role}:** {o.note}")
            for b in o.lead_with:
                L.append(f"  - {b}")
        L.append("")

    if r.evidence:
        L.append("## Requirement-by-requirement evidence")
        L.append("")
        L.append("| Requirement | Type | Status | Best matching line in your resume |")
        L.append("|---|---|---|---|")
        for ev in r.evidence:
            tag = "required" if ev.requirement.required else "preferred"
            match = f"{_cell(ev.best_match_text)} ({_cell(ev.best_match_source, 40)})" if ev.best_match_text else "—"
            L.append(f"| {_cell(ev.requirement.text)} | {tag} | {_status(ev.coverage)} | {match} |")
        L.append("")

    if r.level_notes:
        L.append("## Experience level notes")
        L.append("")
        for n in r.level_notes:
            L.append(f"- {n}")
        L.append("")

    return "\n".join(L)