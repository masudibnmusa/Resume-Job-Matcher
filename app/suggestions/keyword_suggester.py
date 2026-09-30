from app.llm.llm_client import LLMClient
from app.models import KeywordSuggestion, Resume
from app.suggestions.prompt_templates import SYSTEM_TRUTHFUL, keyword_suggestion_prompt
from app.utils import validators


def suggest_keywords(resume: Resume, missing_terms: list[str], llm: LLMClient, limit: int = 10) -> list[KeywordSuggestion]:
    terms = missing_terms[:limit]
    if not terms:
        return []

    snippets = resume.skills[:20]
    for e in resume.experience:
        snippets.extend(e.bullets[:3])
    snippets = snippets[:30]

    data = llm.complete_json(keyword_suggestion_prompt(terms, snippets), system=SYSTEM_TRUTHFUL)
    items = data.get("suggestions", []) if isinstance(data, dict) else []

    resume_text = resume.full_text()
    out: list[KeywordSuggestion] = []
    for item in items:
        if not isinstance(item, dict) or not item.get("term"):
            continue
        example = str(item.get("example", ""))
        if validators.new_numbers(example, resume_text):  # example invents a number
            continue
        condition = str(item.get("condition", "")).strip() or "Only add this if it is true for you."
        out.append(
            KeywordSuggestion(
                term=str(item["term"]),
                where=str(item.get("where", "")),
                example=example,
                condition=condition,
            )
        )
    return out