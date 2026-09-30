from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

RequirementKind = Literal["skill", "responsibility", "education", "experience"]


# ---------- Resume ----------
class Experience(BaseModel):
    title: str = ""
    company: str = ""
    start: str = ""
    end: str = ""
    bullets: list[str] = Field(default_factory=list)


class Education(BaseModel):
    degree: str = ""
    field: str = ""
    institution: str = ""
    year: str = ""


class Resume(BaseModel):
    name: str = ""
    summary: str = ""
    skills: list[str] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    raw_text: str = ""

    def full_text(self) -> str:
        if self.raw_text:
            return self.raw_text
        parts = [self.summary, ", ".join(self.skills)]
        for e in self.experience:
            parts.append(f"{e.title} {e.company}")
            parts.extend(e.bullets)
        for ed in self.education:
            parts.append(f"{ed.degree} {ed.field} {ed.institution}")
        return "\n".join(p for p in parts if p.strip())


# ---------- Job posting ----------
class Requirement(BaseModel):
    text: str
    kind: RequirementKind = "skill"
    required: bool = True
    keywords: list[str] = Field(default_factory=list)


class JobPosting(BaseModel):
    title: str = ""
    company: str = ""
    seniority: str = ""
    min_years: Optional[float] = None
    education_required: str = ""
    requirements: list[Requirement] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


# ---------- Matching / scoring ----------
class Evidence(BaseModel):
    requirement: Requirement
    best_match_text: str = ""
    best_match_source: str = ""
    similarity: float = 0.0
    matched_keywords: list[str] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)
    coverage: float = 0.0  # 0..1, set by fit_scorer


class Gap(BaseModel):
    requirement: str
    required: bool = True
    status: Literal["missing", "weak"]
    severity: Literal["critical", "moderate", "minor"]
    reason: str = ""
    missing_keywords: list[str] = Field(default_factory=list)


class ScoreBreakdown(BaseModel):
    overall: float
    skills: Optional[float] = None
    experience: Optional[float] = None
    education: Optional[float] = None
    semantic_signal: float = 0.0
    keyword_signal: Optional[float] = None
    level_signal: Optional[float] = None


# ---------- Suggestions ----------
class BulletSuggestion(BaseModel):
    role: str
    original: str
    rewritten: str
    reason: str = ""


class KeywordSuggestion(BaseModel):
    term: str
    where: str = ""
    example: str = ""
    condition: str = ""


class ReorderSuggestion(BaseModel):
    role: str
    note: str
    lead_with: list[str] = Field(default_factory=list)


class MatchResult(BaseModel):
    resume: Resume
    job: JobPosting
    score: ScoreBreakdown
    evidence: list[Evidence] = Field(default_factory=list)
    gaps: list[Gap] = Field(default_factory=list)
    keywords_found: list[str] = Field(default_factory=list)
    keywords_missing: list[str] = Field(default_factory=list)
    level_notes: list[str] = Field(default_factory=list)
    bullet_suggestions: list[BulletSuggestion] = Field(default_factory=list)
    keyword_suggestions: list[KeywordSuggestion] = Field(default_factory=list)
    reorder_suggestions: list[ReorderSuggestion] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)