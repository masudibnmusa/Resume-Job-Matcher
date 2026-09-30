import logging
import re
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

from app.llm.llm_client import LLMClient, LLMError
from app.models import JobPosting, Requirement
from app.parsing.section_extractor import BULLET
from app.suggestions.prompt_templates import SYSTEM_EXTRACT, job_extraction_prompt

log = logging.getLogger(__name__)

VALID_KINDS = {"skill", "responsibility", "education", "experience"}
RESP_HDR = ("responsibilit", "what you'll do", "what you will do", "duties", "the role")
REQ_HDR = ("requirement", "qualification", "what you bring", "must have", "looking for", "skills")
PREF_HDR = ("nice to have", "preferred", "bonus", "desirable", "a plus")
SENIORITY_WORDS = ("principal", "staff", "lead", "senior", "junior", "mid", "entry", "intern")
STOP_CAPS = {"and", "the", "experience", "strong", "ability", "knowledge", "familiarity", "proven"}


def _s(v) -> str:
    return "" if v is None else str(v).strip()


# ---------- loading ----------
class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript"}:
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"} and self._skip:
            self._skip -= 1
        if tag in {"p", "li", "div", "br", "h1", "h2", "h3", "h4"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self._skip and data.strip():
            self.parts.append(data.strip() + " ")


def _fetch_url(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (resume-job-matcher)"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        html = resp.read().decode("utf-8", errors="ignore")
    parser = _TextExtractor()
    parser.feed(html)
    text = re.sub(r"\n\s*\n+", "\n", "".join(parser.parts)).strip()
    if len(text) < 200:
        raise ValueError(
            "Could not read the page (login wall or JavaScript-rendered). Paste the posting text into a file instead."
        )
    return text


def load_posting_text(source: str) -> str:
    if source.startswith(("http://", "https://")):
        return _fetch_url(source)
    p = Path(source)
    if len(source) < 500 and p.exists():
        return p.read_text(encoding="utf-8", errors="ignore")
    return source  # treat as pasted text


# ---------- rule-based fallback ----------
def _guess_keywords(text: str) -> list[str]:
    out = []
    words = re.findall(r"[A-Za-z][A-Za-z0-9+#.]*", text)
    for i, w in enumerate(words):
        w = w.strip(".")
        if i == 0 or not w or w.lower() in STOP_CAPS:
            continue
        if w[0].isupper() or any(c in w for c in "+#") or any(c.isdigit() for c in w):
            out.append(w)
    return out


def fallback_posting(text: str) -> JobPosting:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    title = lines[0] if lines else ""
    kind, required = "skill", True
    reqs: list[Requirement] = []
    for line in lines[1:]:
        is_bullet = bool(BULLET.match(line))
        low = line.lower().rstrip(":")
        if not is_bullet and len(line) < 60:
            if any(h in low for h in PREF_HDR):
                kind, required = "skill", False
                continue
            if any(h in low for h in RESP_HDR):
                kind, required = "responsibility", True
                continue
            if any(h in low for h in REQ_HDR):
                kind, required = "skill", True
                continue
        if is_bullet:
            t = BULLET.sub("", line).strip()
            reqs.append(Requirement(text=t, kind=kind, required=required, keywords=_guess_keywords(t)))
    m = re.search(r"(\d+(?:\.\d+)?)\+?\s*(?:years|yrs|year)", text, re.IGNORECASE)
    seniority = next((w for w in SENIORITY_WORDS if w in title.lower()), "")
    job = JobPosting(
        title=title,
        seniority=seniority,
        min_years=float(m.group(1)) if m else None,
        requirements=reqs,
    )
    _merge_keywords(job)
    return job


# ---------- LLM path ----------
def _merge_keywords(job: JobPosting) -> None:
    seen, merged = set(), []
    for k in list(job.keywords) + [k for r in job.requirements for k in r.keywords]:
        if k and k.lower() not in seen:
            seen.add(k.lower())
            merged.append(k)
    job.keywords = merged


def _job_from_dict(d: dict) -> JobPosting:
    reqs = []
    for r in d.get("requirements") or []:
        if not isinstance(r, dict) or not _s(r.get("text")):
            continue
        kind = _s(r.get("kind")).lower()
        reqs.append(
            Requirement(
                text=_s(r.get("text")),
                kind=kind if kind in VALID_KINDS else "skill",
                required=bool(r.get("required", True)),
                keywords=[_s(k) for k in (r.get("keywords") or []) if _s(k)],
            )
        )
    try:
        min_years = float(d["min_years"]) if d.get("min_years") is not None else None
    except (TypeError, ValueError):
        min_years = None
    job = JobPosting(
        title=_s(d.get("title")),
        company=_s(d.get("company")),
        seniority=_s(d.get("seniority")),
        min_years=min_years,
        education_required=_s(d.get("education_required")),
        requirements=reqs,
        keywords=[_s(k) for k in (d.get("keywords") or []) if _s(k)],
    )
    _merge_keywords(job)
    return job


def parse_job_posting(source: str, llm: LLMClient | None = None) -> JobPosting:
    text = load_posting_text(source)
    if llm is not None:
        try:
            data = llm.complete_json(job_extraction_prompt(text), system=SYSTEM_EXTRACT)
            if isinstance(data, dict):
                job = _job_from_dict(data)
                if job.requirements:
                    return job
        except (LLMError, ValueError) as e:
            log.warning("LLM job extraction failed (%s); using rule-based parser.", e)
    return fallback_posting(text)