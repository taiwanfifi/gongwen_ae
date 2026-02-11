# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GongWen-AE is a **Symbolic AutoEncoder for Taiwan Government Documents (台灣公文符號化自編碼器)**. It uses LLMs to decompose government documents into two interpretable latent spaces:

- **Content JSON**: De-bureaucratized semantic information (topic, intent, entities, events, actions) — no formal document language allowed
- **Rules JSON**: Formatting parameters (doc_type, tone, required_sections, sender/receiver, formality_level)

This enables content-format decoupling for research on symbolic disentanglement, closed-loop evaluation, and self-refining agents.

## Common Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Set API key
export OPENAI_API_KEY="your-key"

# POC quick test (20 documents)
python main.py --mode poc --count 5

# Paper 1: Disentanglement (cross-reconstruction + ablation)
python main.py --mode paper1 --count 20

# Paper 2: Closed-loop (cycle consistency + AE vs Direct)
python main.py --mode paper2 --count 20

# Paper 3: Self-refinement loop
python main.py --mode paper3 --count 10

# Re-evaluate existing data
python main.py --mode eval-only
```

## Architecture

### Pipeline Stages

```
Generate → Encode → Decode → Evaluate
```

1. **DataGenerator** (`pipeline.py`): Reverse data generation — creates Content → selects Rules → composes document. Produces perfect ground truth.
2. **Encoder** (`pipeline.py`): Extracts Content JSON and Rules JSON from document text
3. **Decoder** (`pipeline.py`): Reconstructs document from Content + Rules
4. **Evaluator** (`pipeline.py`): 6-dimensional scoring (hard metrics + embedding similarity + LLM judges)

### Core Classes

| Class | File | Purpose |
|-------|------|---------|
| `DataGenerator` | pipeline.py | Reverse generation with ground truth |
| `Encoder` | pipeline.py | Document → (Content, Rules) extraction |
| `Decoder` | pipeline.py | (Content, Rules) → Document reconstruction |
| `Evaluator` | pipeline.py | 6-metric evaluation |
| `DirectGenerator` | pipeline.py | Direct generation baseline (Paper 2) |
| `LLMClient` | client.py | Async OpenAI wrapper with retry, JSON mode, embeddings |

### Data Models (`models.py`)

- `GongWenContent`: topic, intent, key_events, entities, action_items, background
- `GongWenRules`: doc_type, sender_org, receiver_org, tone, required_sections, formality_level, terminology_constraints, has_attachments, speed_class
- `GongWenDocument`, `EncodingResult`, `DecodingResult`, `EvaluationResult`

### Prompts (`prompts.py`)

All LLM prompts use `<output></output>` XML tags for structured responses. Key prompts:
- `GENERATE_CONTENT_SYSTEM/USER` — Content generation
- `COMPOSE_DOCUMENT_SYSTEM/USER` — Document composition
- `ENCODE_CONTENT_SYSTEM`, `ENCODE_RULES_SYSTEM` — Extraction
- `DECODE_DOCUMENT_SYSTEM` — Reconstruction
- `CRITIQUE_SYSTEM`, `REFINE_RULES_SYSTEM` — Paper 3 self-correction

## Evaluation Metrics

| Metric | Type | Weight | Description |
|--------|------|--------|-------------|
| rule_adherence | Hard | 15% | Regex-based format checks (9 items) |
| structural_match | Hard | 10% | gt_rules vs predicted_rules field matching |
| semantic_similarity | Soft | 20% | Embedding cosine: original vs reconstructed |
| content_accuracy | Soft | 25% | Embedding cosine: gt_content vs predicted_content |
| content_preservation | LLM | 15% | LLM judges completeness (1-5 normalized) |
| format_compliance | LLM | 15% | LLM judges format correctness (1-5 normalized) |

## Configuration (`config.py`)

Key settings:
- `LLM_MODEL = "gpt-4o-mini"`, `EMBEDDING_MODEL = "text-embedding-3-small"`
- `POC_COUNT = 20`, `CROSS_RECON_PAIRS = 10`, `CYCLE_CONSISTENCY_N = 10`
- `REFINEMENT_MAX_ITER = 3`, `REFINEMENT_THRESHOLD = 0.92`
- `EVAL_WEIGHTS` dict controls metric weighting

## Experiment Modes

- **poc**: Quick test pipeline
- **paper1**: Cross-reconstruction + ablation (Content-only, Rules-only) — tests disentanglement
- **paper2**: Cycle consistency + AE vs Direct comparison — tests structured bottleneck value
- **paper3**: Score-gated refinement loop — tests self-correction capability
- **eval-only**: Re-evaluate existing generated/encoded/decoded data

## Output Structure

```
data/
├── generated/          # GongWenDocument JSON
├── encoded/            # EncodingResult JSON
├── decoded/            # DecodingResult JSON
└── results/
    ├── poc/            # eval_report.csv
    ├── paper1/         # baseline, cross/, ablation_*/
    ├── paper2/         # ae/, direct/, cycle_consistency.json
    └── paper3/         # refinement_log.json
```
