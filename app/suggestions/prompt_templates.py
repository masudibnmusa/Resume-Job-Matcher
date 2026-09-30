import json

MAX_CHARS = 15000

SYSTEM_EXTRACT = "You extract structured data from documents. You never invent information."

SYSTEM_TRUTHFUL = (
    "You are a careful resume editor. You NEVER fabricate experience, employers, dates, metrics, "
    "tools, or skills. You only rephrase what the candidate has already stated."
)


def resume_extraction_prompt(text: str) -> str:
    return f"""Extract structured data from this resume. Return ONLY valid JSON in this shape:
{{
  "name": "",
  "summary": "",
  "skills": ["..."],
  "experience": [{{"title": "", "company": "", "start": "e.g. Jan 2020", "end": "e.g. Mar 2023 or Present", "bullets": ["..."]}}],
  "education": [{{"degree": "", "field": "", "institution": "", "year": ""}}]
}}
Rules: copy bullets verbatim; do not infer or add anything that is not in the text; use "" for unknown fields.

RESUME:
{text[:MAX_CHARS]}"""


def job_extraction_prompt(text: str) -> str:
    return f"""Extract structured data from this job posting. Return ONLY valid JSON in this shape:
{{
  "title": "", "company": "", "seniority": "e.g. senior, junior, lead, or empty",
  "min_years": null,
  "education_required": "e.g. Bachelor's in Computer Science, or empty",
  "requirements": [
    {{"text": "one requirement, concise", "kind": "skill|responsibility|education|experience",
      "required": true, "keywords": ["specific tools/skills/terms taken literally from the posting"]}}
  ],
  "keywords": ["the most important terms an ATS would scan for"]
}}
Rules: "required" is false for nice-to-have / preferred / bonus items and true for must-haves.
"min_years" is a number (the overall years of experience asked for) or null.
Give each requirement 0-4 keywords, copied literally from the posting.

JOB POSTING:
{text[:MAX_CHARS]}"""


def bullet_rewrite_prompt(
    job_title: str, requirements: list[str], bullets: list[dict], focus_terms: list[str]
) -> str:
    return f"""Rewrite resume bullets so they align better with a job posting ({job_title or "target role"}).

STRICT RULES:
1. Use ONLY facts present in the original bullet. Do not add tools, technologies, team sizes, scope, or outcomes.
2. Do NOT invent numbers. If a metric would strengthen the bullet, put a placeholder like [add metric].
3. Start with a strong action verb, be specific, and keep it to one line.
4. Mirror the posting's language ONLY where it truthfully describes what the bullet already says.
5. If a bullet cannot be improved without inventing facts, leave it out of the output.

Job requirements:
{json.dumps(requirements, indent=1)}

Terms the posting emphasizes (use only if truthful for that bullet):
{json.dumps(focus_terms)}

Bullets to rewrite:
{json.dumps(bullets, indent=1)}

Return ONLY JSON: {{"rewrites": [{{"id": <id>, "rewritten": "...", "reason": "why this fits the posting better"}}]}}"""


def keyword_suggestion_prompt(terms: list[str], resume_snippets: list[str]) -> str:
    return f"""A job posting emphasizes terms that do not appear in a candidate's resume.
For each term, suggest where and how it could be worked in NATURALLY, but only if it is TRUE for the candidate.

STRICT RULES:
- You cannot know whether the candidate has this experience. Every suggestion must state a condition.
- Do not include numbers or specifics in the example that are not in the resume snippets.
- Keep examples short and generic enough that the candidate can adapt them honestly.

Missing terms: {json.dumps(terms)}

Resume snippets for context:
{json.dumps(resume_snippets, indent=1)}

Return ONLY JSON:
{{"suggestions": [{{"term": "", "where": "which resume section or role", "example": "sample phrasing", "condition": "Only add this if ..."}}]}}"""