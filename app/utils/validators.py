import re
from dataclasses import dataclass, field

_NUM = re.compile(r"\$?\d[\d,]*(?:\.\d+)?%?[kKmMbB]?")
_PLACEHOLDER = re.compile(r"\[[^\]]*\]")  # e.g. [add metric] is allowed


@dataclass
class ValidationResult:
    ok: bool
    issues: list[str] = field(default_factory=list)


def _numbers(text: str) -> set[str]:
    text = _PLACEHOLDER.sub("", text)
    return {m.group(0).lower().replace(",", "").replace("$", "") for m in _NUM.finditer(text)}


def _term_tokens(text: str) -> list[str]:
    """Tokens that look like tools, technologies, or proper nouns (skipping the first word)."""
    text = _PLACEHOLDER.sub("", text)
    words = re.findall(r"[A-Za-z][A-Za-z0-9+#./\-]*", text)
    terms = []
    for i, w in enumerate(words):
        w = w.strip(".-/")
        if i == 0 or not w:
            continue
        if w[0].isupper() or any(c.isdigit() or c in "+#" for c in w) or any(c.isupper() for c in w[1:]):
            terms.append(w)
    return terms


def _in_text(term: str, haystack_lower: str) -> bool:
    t = term.lower()
    return t in haystack_lower or (t.endswith("s") and t[:-1] in haystack_lower)


def new_numbers(candidate: str, source: str) -> set[str]:
    return _numbers(candidate) - _numbers(source)


def check_rewrite(original: str, rewritten: str, resume_text: str) -> ValidationResult:
    """Reject rewrites that add facts the resume does not support."""
    issues: list[str] = []

    fresh_nums = new_numbers(rewritten, original)
    if fresh_nums:
        issues.append(f"Introduces numbers not in the original bullet: {sorted(fresh_nums)}")

    resume_lower = resume_text.lower()
    unsupported = [t for t in _term_tokens(rewritten) if not _in_text(t, resume_lower)]
    if unsupported:
        issues.append(f"Mentions terms not found anywhere in the resume: {sorted(set(unsupported))}")

    o_words, r_words = len(original.split()), len(rewritten.split())
    if o_words and r_words > max(o_words * 2.5, o_words + 15):
        issues.append("Rewrite is much longer than the original, which suggests added claims.")

    return ValidationResult(ok=not issues, issues=issues)