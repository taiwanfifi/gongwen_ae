"""Central configuration for gongwen_ae project."""

from pathlib import Path

# ── Paths ──────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
RULES_DIR = DATA_DIR / "rules"
GENERATED_DIR = DATA_DIR / "generated"
ENCODED_DIR = DATA_DIR / "encoded"
DECODED_DIR = DATA_DIR / "decoded"
RESULTS_DIR = DATA_DIR / "results"

# ── Per-Paper Result Paths ─────────────────────────────
RESULTS_POC_DIR = RESULTS_DIR / "poc"
RESULTS_PAPER1_DIR = RESULTS_DIR / "paper1"
RESULTS_PAPER2_DIR = RESULTS_DIR / "paper2"
RESULTS_PAPER3_DIR = RESULTS_DIR / "paper3"

# Ensure directories exist
for d in [
    GENERATED_DIR, ENCODED_DIR, DECODED_DIR, RESULTS_DIR,
    RESULTS_POC_DIR, RESULTS_PAPER1_DIR, RESULTS_PAPER2_DIR, RESULTS_PAPER3_DIR,
]:
    d.mkdir(parents=True, exist_ok=True)

# ── Model Settings ─────────────────────────────────────
LLM_MODEL = "gpt-4o-mini"
EMBEDDING_MODEL = "text-embedding-3-small"
TEMPERATURE = 0.0
TEMPERATURE_CREATIVE = 0.7  # for data generation

# ── Pipeline Settings ──────────────────────────────────
POC_COUNT = 20              # Expanded from 5 → 20 for statistical significance
MAX_RETRIES = 3
RETRY_DELAY = 1.0  # seconds

# ── Eval Weights ───────────────────────────────────────
EVAL_WEIGHTS = {
    "rule_adherence": 0.15,
    "structural_match": 0.10,
    "semantic_similarity": 0.20,
    "content_accuracy": 0.25,
    "content_preservation": 0.15,
    "format_compliance": 0.15,
}

# ── Experiment Settings ───────────────────────────────
CROSS_RECON_PAIRS = 10      # Paper 1: number of cross-reconstruction pairs (from 5 → 10)
CYCLE_CONSISTENCY_N = 10    # Paper 2: number of cycle-consistency samples (from 5 → 10)
REFINEMENT_MAX_ITER = 3     # Paper 3: max self-correction iterations
REFINEMENT_THRESHOLD = 0.92 # Paper 3: stop refining if score >= threshold
