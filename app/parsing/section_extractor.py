import re

from app.models import Education, Experience, Resume

SECTION_ALIASES = {
    "summary": ["summary", "profile", "objective", "about", "professional summary"],
    "skills": ["skills", "technical skills", "core competencies", "technologies", "key skills"],
    "experience": [
        "experience", "work experience", "professional experience",
        "employment", "employment history", "work history",
    ],
    "education": ["education", "academic background", "qualifications", "education & training"],
    "other": ["projects", "certifications", "awards", "publications", "languages", "interests", "volunteer"],
}
_HEADER_LOOKUP = {a: sec for sec, aliases in SECTION_ALIASES.items() for a in aliases}

BULLET = re.compile(r"^\s*[-•*▪·●◦]\s*")
DATE_RANGE = re.compile(
    r"((?:[A-Za-z]{3,9}\.?\s+)?\d{4})\s*(?:-|–|—|to)\s*((?:[A-Za-z]{3,9}\.?\s+)?\d{4}|present|current|now)",
    re.IGNORECASE,
)
DEGREE = re.compile(
    r"\b(bachelor|master|ph\.?d|doctor|mba|b\.?sc|m\.?sc|b\.?a\.?|b\.?s\.?|m\.?a\.?|m\.?s\.?|diploma|associate)\b",
    re.IGNORECASE,
)


def _header_of(line: str) -> str | None:
    if len(line.strip()) > 40:
        return None
    cleaned = re.sub(r"[^a-z &]", "", line.strip().strip(":").lower()).strip()
    return _HEADER_LOOKUP.get(cleaned)


def split_sections(text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {"header": []}
    current = "header"
    for line in text.splitlines():
        sec = _header_of(line)
        if sec:
            current = sec
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)
    return {k: "\n".join(v).strip() for k, v in sections.items()}


def parse_skills(text: str) -> list[str]:
    skills: list[str] = []
    for line in text.splitlines():
        line = BULLET.sub("", line)
        if ":" in line:
            line = line.split(":", 1)[1]
        for part in re.split(r"[,;|•·]", line):
            part = part.strip()
            if 1 < len(part) < 40:
                skills.append(part)
    seen, out = set(), []
    for s in skills:
        if s.lower() not in seen:
            seen.add(s.lower())
            out.append(s)
    return out


def _split_title_company(head: str) -> tuple[str, str]:
    for sep in (" at ", " | ", " - ", " – ", " — ", ", "):
        if sep in head:
            a, b = head.split(sep, 1)
            return a.strip(), b.strip()
    return head.strip(), ""


def parse_experience(text: str) -> list[Experience]:
    roles: list[Experience] = []
    current: Experience | None = None
    prev_plain = ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        is_bullet = bool(BULLET.match(line))
        m = DATE_RANGE.search(line)
        if m and not is_bullet:
            head = (line[: m.start()] + " " + line[m.end():]).strip(" |,-–—()\t")
            if not head:
                head = prev_plain
            title, company = _split_title_company(head)
            current = Experience(title=title, company=company, start=m.group(1), end=m.group(2))
            roles.append(current)
            prev_plain = ""
            continue
        if is_bullet:
            if current:
                current.bullets.append(BULLET.sub("", line).strip())
            continue
        if current and current.bullets and line[0].islower():
            current.bullets[-1] += " " + line  # wrapped bullet
        elif current and not current.bullets and not current.company and len(line) < 60:
            current.company = line
        elif current and len(line) > 60:
            current.bullets.append(line)  # bullet without a marker
        else:
            prev_plain = line
    return roles


def parse_education(text: str) -> list[Education]:
    out: list[Education] = []
    for raw in text.splitlines():
        line = BULLET.sub("", raw).strip()
        if not line:
            continue
        year = re.search(r"\b((?:19|20)\d{2})\b", line)
        if DEGREE.search(line):
            out.append(Education(degree=line, year=year.group(1) if year else ""))
        elif re.search(r"university|college|institute|school", line, re.IGNORECASE) and out:
            if not out[-1].institution:
                out[-1].institution = line
    return out


def rule_based_resume(text: str) -> Resume:
    sections = split_sections(text)
    header_lines = [l.strip() for l in sections.get("header", "").splitlines() if l.strip()]
    name = header_lines[0] if header_lines and len(header_lines[0]) < 60 else ""
    return Resume(
        name=name,
        summary=sections.get("summary", ""),
        skills=parse_skills(sections.get("skills", "")),
        experience=parse_experience(sections.get("experience", "")),
        education=parse_education(sections.get("education", "")),
        raw_text=text,
    )
