# Resume/Job Matcher

Parse a resume and a job posting, score how well they fit, and get specific, honest suggestions for improving the match.

> **Status:** Planned / in design. This README describes the intended behavior and architecture.

## What it does

The matcher compares a resume against a job posting using both meaning (embeddings + LLM reasoning) and literal keywords (the way real ATS filters work). It then produces a scored, annotated report with targeted edits, not generic advice.

- **Semantic matching:** recognizes that "led a team of 6" satisfies "management experience," even without shared keywords.
- **ATS-style keyword check:** flags required terms that never appear literally in the resume.
- **Fit score with breakdown:** overall score plus skills, experience, and education categories.
- **Gap analysis:** e.g. *"Job requires 'stakeholder management', not mentioned in your resume."*
- **Edit suggestions:** rewritten weak bullets, natural ways to work in missing terms, and reordering advice to surface relevant experience.
- **No fabrication:** a validator checks that suggestions don't invent experience, employers, dates, or skills the resume doesn't support.
- **Evidence for every match:** each requirement is linked to the resume line(s) that satisfy it, so the score is explainable.

## How it works

1. **Resume parsing:** extract work experience, skills, education, bullet points, and dates into a fixed schema.
2. **Job posting parsing:** extract required skills, nice-to-haves, responsibilities, seniority, and keywords. Requirements are tagged *required* vs. *preferred*.
3. **Semantic matching:** embed resume sections and job requirements; compute similarity to find overlaps and gaps.
4. **Keyword/ATS check:** literal scan for required terms.
5. **Experience-level match:** compare years and seniority required vs. held.
6. **Fit scoring:** combine semantic similarity, keyword coverage, and experience match using configurable weights.
7. **Gap identification:** flag missing or underrepresented requirements.
8. **Suggestions:** LLM-generated rewrites and keyword placement, checked by the validator.
9. **Report:** scored, annotated output exported as Markdown, HTML, or PDF.

## Data flow

```
Resume (PDF/DOCX) ──► resume_parser.py ──┐
                                         ├──► semantic_matcher.py ──► fit_scorer.py
Job posting (text/URL) ──► job_posting_parser.py ──┘        │
                                                       keyword_matcher.py
                                                            │
                                                       gap_analyzer.py
                                                            │
                                       bullet_rewriter.py / keyword_suggester.py
                                                            │
                                                     report_builder.py
                                                            │
                                                   Final scored report
```

## Project structure

```
resume-job-matcher/
├── app/
│   ├── main.py                          # Entry point (CLI first, Streamlit later)
│   ├── config.py                        # API keys, scoring weights
│   ├── models.py                        # Schemas for parsed resume/posting/results
│   ├── parsing/
│   │   ├── resume_parser.py             # PDF/DOCX -> structured data
│   │   ├── job_posting_parser.py        # Text/URL -> requirements
│   │   └── section_extractor.py         # Experience / skills / education split
│   ├── matching/
│   │   ├── embedder.py                  # Embed resume sections + requirements
│   │   ├── semantic_matcher.py          # Similarity scoring
│   │   ├── keyword_matcher.py           # Literal ATS-style matching
│   │   └── experience_level_matcher.py  # Seniority / years required vs. held
│   ├── scoring/
│   │   ├── fit_scorer.py                # Overall + category scores
│   │   └── gap_analyzer.py              # Missing skills/keywords/experience
│   ├── suggestions/
│   │   ├── bullet_rewriter.py           # Improve weak bullets
│   │   ├── keyword_suggester.py         # Natural ways to include missing terms
│   │   ├── reorder_suggester.py         # Reorder to highlight relevant experience
│   │   └── prompt_templates.py
│   ├── llm/
│   │   └── llm_client.py                # Claude/GPT API wrapper
│   ├── report/
│   │   ├── report_builder.py            # Compile score + gaps + suggestions
│   │   └── exporter.py                  # PDF / Markdown / HTML
│   └── utils/
│       └── validators.py                # Guard against fabricated experience
├── data/
│   ├── resumes/
│   ├── job_postings/
│   └── reports/
├── tests/
├── .env.example
├── requirements.txt
├── README.md
└── run.sh
```

## Getting started

```bash
git clone https://github.com/masudibnmusa/Resume-Job-Matcher.git
cd resume-job-matcher

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # then add your API key(s)
```

### Usage (planned CLI)

```bash
python -m app.main \
  --resume data/resumes/my_resume.pdf \
  --job data/job_postings/posting.txt \
  --output data/reports/report.md
```

Job postings are read from pasted/saved text. URL fetching is a later feature, since many job sites block scrapers or render content with JavaScript.

## Configuration

Set in `.env`:

| Variable | Purpose |
|---|---|
| `LLM_API_KEY` | API key for the LLM provider |
| `LLM_MODEL` | Model used for parsing and suggestions |
| `EMBEDDING_MODEL` | Model used for semantic matching |

Scoring weights (semantic, keyword, experience, and per-category) live in `app/config.py`.

## Scoring

The overall score combines three signals:

- **Semantic similarity** between resume content and job requirements
- **Keyword coverage** of required and preferred terms (required terms weigh more)
- **Experience-level match** on years and seniority

The default weights are starting points, not ground truth. Calibrate them against hand-rated resume/job pairs before trusting the numbers.

## Testing

```bash
pytest
```

Tests cover the parsers, semantic matcher, keyword matcher, fit scorer, gap analyzer, bullet rewriter, and validator.

## Privacy

Resumes contain personal information. Be aware that:

- Resume and job text is sent to the configured LLM/embedding API for parsing and suggestions.
- Files in `data/` are stored locally and are git-ignored by default. Delete them when you're done.
- Review your LLM provider's data-retention policy before using real resumes.

## Limitations

- Resume layouts vary widely (columns, tables, graphics), so parsing may miss or misfile content.
- Years-of-experience per skill is estimated from date ranges and can be off.
- The fit score is an aid to judgment, not a prediction of hiring outcomes or of any specific ATS's behavior.
- Suggestions must be reviewed by you. Only claim what is true.

## License

MIT