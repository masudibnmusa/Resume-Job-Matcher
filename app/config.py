import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BASE_DIR / "data" / "reports"

# --- LLM / embeddings ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "claude-sonnet-5-5")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# --- Category weights for the overall score (renormalized if a category is n/a) ---
CATEGORY_WEIGHTS = {"skills": 0.50, "experience": 0.35, "education": 0.15}

# --- Per-requirement coverage: blend of semantic + keyword evidence ---
SEMANTIC_WEIGHT = 0.6
KEYWORD_WEIGHT = 0.4
KEYWORD_FLOOR = 0.7  # a skill whose keywords are all present literally gets at least this

# Cosine similarity range (MiniLM-style) mapped onto 0..1
SIM_LOW = 0.30
SIM_HIGH = 0.65

# Required requirements count more than preferred ones
REQUIRED_WEIGHT = 2.0
PREFERRED_WEIGHT = 1.0

# Coverage thresholds for gap detection
MISSING_THRESHOLD = 0.25
WEAK_THRESHOLD = 0.60