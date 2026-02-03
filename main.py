"""End-to-end pipeline for gongwen_ae.

Usage:
    python main.py --mode poc --count 2       # Quick test with 2 docs
    python main.py --mode poc                  # Full POC with 5 docs
    python main.py --mode full --count 10      # Larger run
    python main.py --mode eval-only            # Re-evaluate existing data
    python main.py --mode paper1 --count 3     # Cross-reconstruction + ablation
    python main.py --mode paper2 --count 3     # Cycle consistency + baseline
    python main.py --mode paper3 --count 2     # Self-correction loop
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
from pathlib import Path

from config import (
    CROSS_RECON_PAIRS,
    CYCLE_CONSISTENCY_N,
    DECODED_DIR,
    ENCODED_DIR,
    GENERATED_DIR,
    POC_COUNT,
    REFINEMENT_MAX_ITER,
    REFINEMENT_THRESHOLD,
    RESULTS_PAPER1_DIR,
    RESULTS_PAPER2_DIR,
    RESULTS_PAPER3_DIR,
    RESULTS_POC_DIR,
    TEMPERATURE_CREATIVE,
)
from client import LLMClient
from models import (
    DecodingResult,
    EncodingResult,
    GongWenContent,
    GongWenDocument,
    GongWenRules,
)
from pipeline import DataGenerator, DirectGenerator, Decoder, Encoder, Evaluator
from prompts import (
    CRITIQUE_SYSTEM,
    CRITIQUE_USER,
    REFINE_RULES_SYSTEM,
    REFINE_RULES_USER,
    RULE_TEMPLATES,
    TOPIC_POOL,
)


# ═══════════════════════════════════════════════════════════════════
#  Original modes: poc / full / eval-only
# ═══════════════════════════════════════════════════════════════════

async def run_full_pipeline(count: int) -> None:
    """Run generate → encode → decode → evaluate."""
    client = LLMClient()

    # Phase 1: Generate
    print("\n" + "=" * 60)
    print("  PHASE 1: REVERSE DATA GENERATION")
    print("=" * 60)
    generator = DataGenerator(client)
    docs = await generator.generate_batch(count)

    # Phase 2: Encode
    print("\n" + "=" * 60)
    print("  PHASE 2: ENCODE")
    print("=" * 60)
    encoder = Encoder(client)
    encodings = await encoder.encode_batch(docs)

    # Phase 3: Decode
    print("\n" + "=" * 60)
    print("  PHASE 3: DECODE")
    print("=" * 60)
    decoder = Decoder(client)
    decodings = await decoder.decode_batch(encodings)

    # Phase 4: Evaluate
    print("\n" + "=" * 60)
    print("  PHASE 4: EVALUATE")
    print("=" * 60)
    evaluator = Evaluator(client)
    await evaluator.evaluate_batch(docs, encodings, decodings, output_dir=RESULTS_POC_DIR)


async def run_eval_only() -> None:
    """Re-evaluate from saved files."""
    client = LLMClient()

    # Load all saved data
    docs: list[GongWenDocument] = []
    encodings: list[EncodingResult] = []
    decodings: list[DecodingResult] = []

    for gen_file in sorted(GENERATED_DIR.glob("*.json")):
        doc_id = gen_file.stem
        enc_file = ENCODED_DIR / f"{doc_id}.json"
        dec_file = DECODED_DIR / f"{doc_id}.json"

        if not enc_file.exists() or not dec_file.exists():
            print(f"  [skip] {doc_id}: missing encoded or decoded file")
            continue

        docs.append(GongWenDocument(**json.loads(gen_file.read_text(encoding="utf-8"))))
        encodings.append(EncodingResult(**json.loads(enc_file.read_text(encoding="utf-8"))))
        decodings.append(DecodingResult(**json.loads(dec_file.read_text(encoding="utf-8"))))

    if not docs:
        print("No data found. Run full pipeline first.")
        return

    print(f"Loaded {len(docs)} documents for re-evaluation.")
    evaluator = Evaluator(client)
    await evaluator.evaluate_batch(docs, encodings, decodings, output_dir=RESULTS_POC_DIR)


# ═══════════════════════════════════════════════════════════════════
#  Paper 1: Cross-reconstruction + ablation
# ═══════════════════════════════════════════════════════════════════

async def run_paper1(count: int) -> None:
    """Paper 1 experiments: cross-reconstruction (C_A, S_B) and ablation.

    1. Generate N documents → encode each to (content, rules).
    2. Cross-reconstruction: pair content_i with rules_j (i≠j), decode, evaluate.
    3. Ablation: content-only (zero out rules) and rules-only (zero out content).
    """
    client = LLMClient()
    generator = DataGenerator(client)
    encoder = Encoder(client)
    decoder = Decoder(client)
    evaluator = Evaluator(client)

    # ── Generate & Encode ──────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  PAPER 1 — GENERATE & ENCODE")
    print("=" * 60)
    docs = await generator.generate_batch(count)
    encodings = await encoder.encode_batch(docs)

    # ── Normal reconstruction (baseline) ──────────────────────────
    print("\n" + "=" * 60)
    print("  PAPER 1 — NORMAL RECONSTRUCTION (baseline)")
    print("=" * 60)
    decodings = await decoder.decode_batch(encodings)
    await evaluator.evaluate_batch(
        docs, encodings, decodings,
        output_dir=RESULTS_PAPER1_DIR,
    )

    # ── Cross-reconstruction ──────────────────────────────────────
    print("\n" + "=" * 60)
    print("  PAPER 1 — CROSS-RECONSTRUCTION")
    print("=" * 60)
    n_pairs = min(CROSS_RECON_PAIRS, len(encodings) * (len(encodings) - 1))
    pairs_done = 0

    cross_docs: list[GongWenDocument] = []
    cross_encodings: list[EncodingResult] = []
    cross_decodings: list[DecodingResult] = []

    for i in range(len(encodings)):
        for j in range(len(encodings)):
            if i == j:
                continue
            if pairs_done >= n_pairs:
                break
            # Mix content from i with rules from j
            cross_enc = EncodingResult(
                doc_id=f"cross_{encodings[i].doc_id}_{encodings[j].doc_id}",
                predicted_content=encodings[i].predicted_content,
                predicted_rules=encodings[j].predicted_rules,
            )
            cross_dec = await decoder.decode_one(cross_enc)
            # Use doc_i as the reference for content comparison
            cross_doc = GongWenDocument(
                doc_id=cross_enc.doc_id,
                full_text=docs[i].full_text,
                gt_content=docs[i].gt_content,
                gt_rules=docs[j].gt_rules,
            )
            cross_docs.append(cross_doc)
            cross_encodings.append(cross_enc)
            cross_decodings.append(cross_dec)
            pairs_done += 1
            print(f"  [cross] pair {pairs_done}/{n_pairs}: "
                  f"content={encodings[i].doc_id}, rules={encodings[j].doc_id}")
        if pairs_done >= n_pairs:
            break

    if cross_docs:
        print("\n  Evaluating cross-reconstruction results...")
        cross_dir = RESULTS_PAPER1_DIR / "cross"
        cross_dir.mkdir(parents=True, exist_ok=True)
        await evaluator.evaluate_batch(
            cross_docs, cross_encodings, cross_decodings,
            output_dir=cross_dir,
        )

    # ── Ablation: content-only ─────────────────────────────────────
    print("\n" + "=" * 60)
    print("  PAPER 1 — ABLATION: CONTENT-ONLY (rules zeroed)")
    print("=" * 60)
    default_rules = GongWenRules(
        doc_type="函",
        sender_org="（未指定）",
        receiver_org="（未指定）",
        tone="平行",
        required_sections=["主旨", "說明"],
        formality_level="高",
        terminology_constraints=[],
        has_attachments=False,
        speed_class="普通件",
    )
    ablation_content_encs: list[EncodingResult] = []
    for enc in encodings:
        ablation_content_encs.append(EncodingResult(
            doc_id=f"abl_content_{enc.doc_id}",
            predicted_content=enc.predicted_content,
            predicted_rules=default_rules,
        ))
    abl_content_decs = await decoder.decode_batch(ablation_content_encs)
    abl_content_docs = [
        GongWenDocument(
            doc_id=f"abl_content_{d.doc_id}",
            full_text=d.full_text,
            gt_content=d.gt_content,
            gt_rules=d.gt_rules,
        )
        for d in docs
    ]
    abl_content_dir = RESULTS_PAPER1_DIR / "ablation_content_only"
    abl_content_dir.mkdir(parents=True, exist_ok=True)
    await evaluator.evaluate_batch(
        abl_content_docs, ablation_content_encs, abl_content_decs,
        output_dir=abl_content_dir,
    )

    # ── Ablation: rules-only ──────────────────────────────────────
    print("\n" + "=" * 60)
    print("  PAPER 1 — ABLATION: RULES-ONLY (content zeroed)")
    print("=" * 60)
    default_content = GongWenContent(
        topic="（未指定主題）",
        intent="（未指定意圖）",
        key_events=[],
        entities=[],
        action_items=[],
        background="",
    )
    ablation_rules_encs: list[EncodingResult] = []
    for enc in encodings:
        ablation_rules_encs.append(EncodingResult(
            doc_id=f"abl_rules_{enc.doc_id}",
            predicted_content=default_content,
            predicted_rules=enc.predicted_rules,
        ))
    abl_rules_decs = await decoder.decode_batch(ablation_rules_encs)
    abl_rules_docs = [
        GongWenDocument(
            doc_id=f"abl_rules_{d.doc_id}",
            full_text=d.full_text,
            gt_content=d.gt_content,
            gt_rules=d.gt_rules,
        )
        for d in docs
    ]
    abl_rules_dir = RESULTS_PAPER1_DIR / "ablation_rules_only"
    abl_rules_dir.mkdir(parents=True, exist_ok=True)
    await evaluator.evaluate_batch(
        abl_rules_docs, ablation_rules_encs, abl_rules_decs,
        output_dir=abl_rules_dir,
    )

    print("\n" + "=" * 60)
    print("  PAPER 1 — COMPLETE")
    print("=" * 60)


# ═══════════════════════════════════════════════════════════════════
#  Paper 2: Cycle consistency + baseline comparison
# ═══════════════════════════════════════════════════════════════════

async def run_paper2(count: int) -> None:
    """Paper 2 experiments: cycle consistency and baseline (DirectGenerator vs AE).

    1. AE path: Generate → Encode → Decode → Re-Encode → compare latent vectors.
    2. Baseline: DirectGenerator produces docs from same topic + rules; evaluate both.
    """
    client = LLMClient()
    generator = DataGenerator(client)
    encoder = Encoder(client)
    decoder = Decoder(client)
    evaluator = Evaluator(client)
    direct_gen = DirectGenerator(client)

    # ── Generate & full AE pass ───────────────────────────────────
    print("\n" + "=" * 60)
    print("  PAPER 2 — GENERATE & AE PASS")
    print("=" * 60)
    docs = await generator.generate_batch(count)
    encodings = await encoder.encode_batch(docs)
    decodings = await decoder.decode_batch(encodings)

    # ── Cycle consistency: re-encode reconstructed text ───────────
    print("\n" + "=" * 60)
    print("  PAPER 2 — CYCLE CONSISTENCY (Re-Encode)")
    print("=" * 60)
    n_cycle = min(CYCLE_CONSISTENCY_N, len(docs))
    cycle_results: list[dict] = []

    for idx in range(n_cycle):
        dec = decodings[idx]
        enc1 = encodings[idx]

        # Create a pseudo-document from the reconstructed text for re-encoding
        pseudo_doc = GongWenDocument(
            doc_id=f"cycle_{dec.doc_id}",
            full_text=dec.reconstructed_text,
            gt_content=docs[idx].gt_content,
            gt_rules=docs[idx].gt_rules,
        )
        enc2 = await encoder.encode_one(pseudo_doc)

        # Compare latent vectors: enc1 vs enc2
        content1_str = json.dumps(enc1.predicted_content.model_dump(), ensure_ascii=False)
        content2_str = json.dumps(enc2.predicted_content.model_dump(), ensure_ascii=False)
        rules1_str = json.dumps(enc1.predicted_rules.model_dump(), ensure_ascii=False)
        rules2_str = json.dumps(enc2.predicted_rules.model_dump(), ensure_ascii=False)

        emb_c1, emb_c2, emb_r1, emb_r2 = await client.embed_batch(
            [content1_str, content2_str, rules1_str, rules2_str]
        )
        content_sim = LLMClient.cosine_similarity(emb_c1, emb_c2)
        rules_sim = LLMClient.cosine_similarity(emb_r1, emb_r2)

        cycle_results.append({
            "doc_id": dec.doc_id,
            "content_similarity": content_sim,
            "rules_similarity": rules_sim,
        })
        print(f"  [cycle] {dec.doc_id}: content_sim={content_sim:.4f}, rules_sim={rules_sim:.4f}")

    # Save cycle results
    cycle_path = RESULTS_PAPER2_DIR / "cycle_consistency.json"
    cycle_path.write_text(
        json.dumps(cycle_results, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\n📝 Cycle consistency results saved to {cycle_path}")

    # ── Baseline comparison: DirectGenerator vs AE ─────────────────
    print("\n" + "=" * 60)
    print("  PAPER 2 — BASELINE COMPARISON (Direct vs AE)")
    print("=" * 60)

    # Generate direct docs with same topic + rules as the AE docs
    topics = [d.gt_content.topic for d in docs]
    rules_list = [d.gt_rules for d in docs]
    direct_texts = await direct_gen.generate_batch(topics, rules_list)

    # Evaluate AE reconstructions
    print("\n  Evaluating AE reconstructions...")
    ae_dir = RESULTS_PAPER2_DIR / "ae"
    ae_dir.mkdir(parents=True, exist_ok=True)
    await evaluator.evaluate_batch(
        docs, encodings, decodings, output_dir=ae_dir,
    )

    # Evaluate direct-generated docs — encode them first for fair comparison
    # (otherwise content_accuracy and structural_match get a free 1.0)
    print("\n  Encoding direct-generated documents for fair comparison...")
    direct_encode_docs = [
        GongWenDocument(
            doc_id=f"direct_{d.doc_id}",
            full_text=text,
            gt_content=d.gt_content,
            gt_rules=d.gt_rules,
        )
        for d, text in zip(docs, direct_texts)
    ]
    direct_encodings = await encoder.encode_batch(direct_encode_docs)

    print("\n  Evaluating direct-generated documents...")
    direct_decodings = [
        DecodingResult(doc_id=f"direct_{d.doc_id}", reconstructed_text=text)
        for d, text in zip(docs, direct_texts)
    ]
    # Use ORIGINAL full_text for evaluation (semantic_similarity compares original vs direct)
    direct_docs = [
        GongWenDocument(
            doc_id=f"direct_{d.doc_id}",
            full_text=d.full_text,
            gt_content=d.gt_content,
            gt_rules=d.gt_rules,
        )
        for d in docs
    ]
    direct_dir = RESULTS_PAPER2_DIR / "direct"
    direct_dir.mkdir(parents=True, exist_ok=True)
    await evaluator.evaluate_batch(
        direct_docs, direct_encodings, direct_decodings, output_dir=direct_dir,
    )

    print("\n" + "=" * 60)
    print("  PAPER 2 — COMPLETE")
    print("=" * 60)


# ═══════════════════════════════════════════════════════════════════
#  Paper 3: Self-correction loop
# ═══════════════════════════════════════════════════════════════════

async def run_paper3(count: int) -> None:
    """Paper 3 experiments: self-correction loop.

    For each document:
    1. Generate → Encode → Decode → Evaluate.
    2. If score < threshold: Critique → Refine Rules → Re-Decode → Re-Evaluate.
    3. Repeat up to REFINEMENT_MAX_ITER times.
    """
    client = LLMClient()
    generator = DataGenerator(client)
    encoder = Encoder(client)
    decoder = Decoder(client)
    evaluator = Evaluator(client)

    # ── Generate & Encode ──────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  PAPER 3 — GENERATE & ENCODE")
    print("=" * 60)
    docs = await generator.generate_batch(count)
    encodings = await encoder.encode_batch(docs)

    all_iterations: list[dict] = []

    for doc_idx, (doc, enc) in enumerate(zip(docs, encodings)):
        print(f"\n{'=' * 60}")
        print(f"  PAPER 3 — SELF-CORRECTION: doc {doc_idx+1}/{len(docs)} ({doc.doc_id})")
        print(f"{'=' * 60}")

        current_rules = enc.predicted_rules
        best_score = 0.0
        best_rules = current_rules
        iteration_log: list[dict] = []

        for iteration in range(REFINEMENT_MAX_ITER + 1):
            # Decode with current rules
            current_enc = EncodingResult(
                doc_id=f"{doc.doc_id}_iter{iteration}",
                predicted_content=enc.predicted_content,
                predicted_rules=current_rules,
            )
            dec = await decoder.decode_one(current_enc)

            # Evaluate
            eval_result = await evaluator.evaluate_one(doc, current_enc, dec)
            score = eval_result.scores.weighted_total
            print(f"  [iter {iteration}] score: {score:.4f}")

            # ── Score-gated acceptance ──
            accepted = False
            if score > best_score:
                best_score = score
                best_rules = current_rules
                accepted = True
                print(f"  [iter {iteration}] ✓ accepted (best so far)")
            else:
                print(f"  [iter {iteration}] ✗ rejected (score <= best {best_score:.4f})")

            iteration_log.append({
                "iteration": iteration,
                "score": score,
                "accepted": accepted,
                "rules": current_rules.model_dump(),
                "reconstructed_length": len(dec.reconstructed_text),
            })

            if score >= REFINEMENT_THRESHOLD:
                print(f"  [iter {iteration}] score >= {REFINEMENT_THRESHOLD}, stopping.")
                break

            if iteration == REFINEMENT_MAX_ITER:
                print(f"  [iter {iteration}] max iterations reached, stopping.")
                break

            # Critique
            print(f"  [iter {iteration}] score < {REFINEMENT_THRESHOLD}, running critique...")
            rules_json = json.dumps(current_rules.model_dump(), ensure_ascii=False, indent=2)
            critique_dict = await client.chat_json(
                system=CRITIQUE_SYSTEM,
                user=CRITIQUE_USER.format(
                    original_text=doc.full_text,
                    reconstructed_text=dec.reconstructed_text,
                    rules_json=rules_json,
                ),
            )
            print(f"  [critique] issues: content={len(critique_dict.get('content_issues', []))}, "
                  f"format={len(critique_dict.get('format_issues', []))}, "
                  f"rules={len(critique_dict.get('rule_violations', []))}")

            iteration_log[-1]["critique"] = critique_dict

            # Refine rules
            refined_dict = await client.chat_json(
                system=REFINE_RULES_SYSTEM,
                user=REFINE_RULES_USER.format(
                    rules_json=rules_json,
                    critique_json=json.dumps(critique_dict, ensure_ascii=False, indent=2),
                ),
            )
            current_rules = GongWenRules(**refined_dict)
            print(f"  [refine] updated rules: {current_rules.doc_type} / {current_rules.tone}")

        all_iterations.append({
            "doc_id": doc.doc_id,
            "iterations": iteration_log,
            "best_score": best_score,
        })

    # Save iteration log
    log_path = RESULTS_PAPER3_DIR / "refinement_log.json"
    log_path.write_text(
        json.dumps(all_iterations, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\n📝 Refinement log saved to {log_path}")

    # Final summary
    print("\n" + "=" * 60)
    print("  PAPER 3 — REFINEMENT SUMMARY")
    print("=" * 60)
    for entry in all_iterations:
        iters = entry["iterations"]
        first_score = iters[0]["score"]
        best_score = entry["best_score"]
        delta = best_score - first_score
        print(f"  {entry['doc_id']}: {first_score:.4f} → {best_score:.4f} (best) "
              f"(Δ={delta:+.4f}, {len(iters)} iterations)")
    print("=" * 60)


# ═══════════════════════════════════════════════════════════════════
#  CLI entry point
# ═══════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(description="gongwen_ae: Official Document AutoEncoder")
    parser.add_argument(
        "--mode",
        choices=["poc", "full", "eval-only", "paper1", "paper2", "paper3"],
        default="poc",
        help="Pipeline mode (default: poc)",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=None,
        help="Number of documents to generate (default: 5 for poc)",
    )
    args = parser.parse_args()

    if args.mode == "eval-only":
        asyncio.run(run_eval_only())
    elif args.mode == "paper1":
        count = args.count or POC_COUNT
        print(f"Running paper1 mode with {count} documents...")
        asyncio.run(run_paper1(count))
    elif args.mode == "paper2":
        count = args.count or POC_COUNT
        print(f"Running paper2 mode with {count} documents...")
        asyncio.run(run_paper2(count))
    elif args.mode == "paper3":
        count = args.count or POC_COUNT
        print(f"Running paper3 mode with {count} documents...")
        asyncio.run(run_paper3(count))
    else:
        count = args.count or POC_COUNT
        print(f"Running {args.mode} mode with {count} documents...")
        asyncio.run(run_full_pipeline(count))


if __name__ == "__main__":
    main()
