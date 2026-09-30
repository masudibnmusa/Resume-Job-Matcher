import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from app import config
from app.llm.llm_client import LLMClient, LLMError
from app.matching import experience_level_matcher, keyword_matcher, semantic_matcher
from app.models import MatchResult
from app.parsing.job_posting_parser import parse_job_posting
from app.parsing.resume_parser import parse_resume
from app.report import exporter, report_builder
from app.scoring import fit_scorer, gap_analyzer
from app.suggestions import bullet_rewriter, keyword_suggester, reorder_suggester


def run_pipeline(resume_path: str, job_source: str, use_llm: bool = True, max_bullets: int = 5) -> MatchResult:
    warnings: list[str] = []

    llm = None
    if use_llm:
        try:
            llm = LLMClient()
        except LLMError as e:
            warnings.append(f"LLM features disabled: {e}")
    else:
        warnings.append("Ran without an LLM: rule-based parsing, and no rewrite or keyword suggestions.")

    resume = parse_resume(resume_path, llm)
    job = parse_job_posting(job_source, llm)
    if not job.requirements:
        raise ValueError("No requirements could be extracted from the job posting.")
    if not resume.experience and not resume.skills:
        warnings.append("Little structured data was extracted from the resume; results may be unreliable.")

    resume_text = resume.full_text()

    evidence = semantic_matcher.match_requirements(resume, job)
    keyword_matcher.apply_keyword_match(evidence, resume_text)
    kw_found, kw_missing = keyword_matcher.job_keyword_coverage(resume_text, job)
    fit_scorer.score_evidence(evidence)

    level_score, level_notes = experience_level_matcher.level_match(resume, job)
    score = fit_scorer.score_match(resume, job, evidence, level_score, kw_found, kw_missing)
    gaps = gap_analyzer.analyze_gaps(evidence, job, score, level_score, level_notes)

    bullet_suggestions, keyword_suggestions = [], []
    if llm is not None:
        try:
            bullet_suggestions, rejected = bullet_rewriter.rewrite_bullets(resume, job, gaps, llm, max_bullets)
            if rejected:
                warnings.append(
                    f"{rejected} suggested rewrite(s) were discarded because they added details "
                    "not supported by your resume."
                )
        except Exception as e:
            warnings.append(f"Bullet rewriting failed: {e}")
        try:
            terms = list(kw_missing) + [k for g in gaps for k in g.missing_keywords]
            terms = list({t.lower(): t for t in terms}.values())
            keyword_suggestions = keyword_suggester.suggest_keywords(resume, terms, llm)
        except Exception as e:
            warnings.append(f"Keyword suggestions failed: {e}")

    reorder = reorder_suggester.suggest_reorder(resume, job, score)

    return MatchResult(
        resume=resume,
        job=job,
        score=score,
        evidence=evidence,
        gaps=gaps,
        keywords_found=kw_found,
        keywords_missing=kw_missing,
        level_notes=level_notes,
        bullet_suggestions=bullet_suggestions,
        keyword_suggestions=keyword_suggestions,
        reorder_suggestions=reorder,
        warnings=warnings,
    )


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Score a resume against a job posting and suggest edits.")
    p.add_argument("--resume", required=True, help="Path to resume (.pdf, .docx, .txt)")
    p.add_argument("--job", required=True, help="Path to posting text, a URL, or '-' to read from stdin")
    p.add_argument("--output", help="Report path (.md, .html, .pdf). Default: data/reports/<name>_<time>.md")
    p.add_argument("--no-llm", action="store_true", help="Skip all LLM calls")
    p.add_argument("--max-bullets", type=int, default=5, help="Max bullets to rewrite")
    p.add_argument("-v", "--verbose", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING, format="%(levelname)s: %(message)s")

    job_source = sys.stdin.read() if args.job == "-" else args.job
    try:
        result = run_pipeline(args.resume, job_source, use_llm=not args.no_llm, max_bullets=args.max_bullets)
    except (ValueError, FileNotFoundError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    out = args.output or str(
        config.REPORTS_DIR / f"{Path(args.resume).stem}_{datetime.now():%Y%m%d_%H%M%S}.md"
    )
    path = exporter.export_report(report_builder.build_report(result), out)

    s = result.score
    print(f"Overall fit: {s.overall:.0f}/100")
    print(f"  Skills: {s.skills}  Experience: {s.experience}  Education: {s.education}")
    print(f"  Gaps: {len(result.gaps)}  Bullet rewrites: {len(result.bullet_suggestions)}")
    print(f"Report saved to {path}")
    for w in result.warnings:
        print(f"Note: {w}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())