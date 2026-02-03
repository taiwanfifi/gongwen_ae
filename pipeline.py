"""All pipeline stages for the gongwen_ae project.

Merged from:
  pipelines/data_generator.py → DataGenerator
  pipelines/encoder.py        → Encoder
  pipelines/decoder.py        → Decoder
  pipelines/evaluator.py      → Evaluator

New additions:
  DirectGenerator → Paper 2 baseline (direct LLM document generation)
"""

from __future__ import annotations

import asyncio
import csv
import json
import random
import re
import uuid
from pathlib import Path

from config import (
    DECODED_DIR,
    ENCODED_DIR,
    EVAL_WEIGHTS,
    GENERATED_DIR,
    RESULTS_DIR,
    RULES_DIR,
    TEMPERATURE_CREATIVE,
)
from client import LLMClient
from models import (
    DecodingResult,
    EncodingResult,
    EvalResult,
    EvalScores,
    GongWenContent,
    GongWenDocument,
    GongWenRules,
)
from prompts import (
    COMPOSE_DOCUMENT_SYSTEM,
    COMPOSE_DOCUMENT_USER,
    DECODE_DOCUMENT_SYSTEM,
    DECODE_DOCUMENT_USER,
    DIRECT_GENERATE_SYSTEM,
    DIRECT_GENERATE_USER,
    ENCODE_CONTENT_SYSTEM,
    ENCODE_CONTENT_USER,
    ENCODE_RULES_SYSTEM,
    ENCODE_RULES_USER,
    GENERATE_CONTENT_SYSTEM,
    GENERATE_CONTENT_USER,
    JUDGE_CONTENT_PRESERVATION_SYSTEM,
    JUDGE_CONTENT_PRESERVATION_USER,
    JUDGE_FORMAT_COMPLIANCE_SYSTEM,
    JUDGE_FORMAT_COMPLIANCE_USER,
    RULE_TEMPLATES,
    TOPIC_POOL,
)


# ── Shared helper ──────────────────────────────────────────────────

def _load_rules_reference() -> str:
    """Load gongwen_rules.md — used by DataGenerator, Decoder, and DirectGenerator."""
    path = RULES_DIR / "gongwen_rules.md"
    return path.read_text(encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════
#  DataGenerator (Phase 1 — reverse data generation)
# ═══════════════════════════════════════════════════════════════════

class DataGenerator:
    """Generates synthetic official documents with ground-truth labels."""

    def __init__(self, client: LLMClient) -> None:
        self.client = client
        self._rules_ref = _load_rules_reference()

    async def generate_one(self, topic: str | None = None) -> GongWenDocument:
        """Generate a single document with ground truth."""
        # Step 1: Pick topic
        topic = topic or random.choice(TOPIC_POOL)
        print(f"  [gen] topic: {topic}")

        # Step 2: LLM generates content JSON
        content_dict = await self.client.chat_json(
            system=GENERATE_CONTENT_SYSTEM,
            user=GENERATE_CONTENT_USER.format(topic=topic),
            temperature=TEMPERATURE_CREATIVE,
        )
        gt_content = GongWenContent(**content_dict)
        print(f"  [gen] content generated: {gt_content.topic}")

        # Step 3: Randomly select rules template
        rules_dict = random.choice(RULE_TEMPLATES)
        gt_rules = GongWenRules(**rules_dict)
        print(f"  [gen] rules selected: {gt_rules.doc_type} / {gt_rules.tone}")

        # Step 4: LLM composes full document
        full_text = await self.client.chat(
            system=COMPOSE_DOCUMENT_SYSTEM.format(rules_reference=self._rules_ref),
            user=COMPOSE_DOCUMENT_USER.format(
                content_json=json.dumps(content_dict, ensure_ascii=False, indent=2),
                rules_json=json.dumps(rules_dict, ensure_ascii=False, indent=2),
            ),
            temperature=TEMPERATURE_CREATIVE,
        )
        print(f"  [gen] document composed ({len(full_text)} chars)")

        doc = GongWenDocument(
            doc_id=str(uuid.uuid4())[:8],
            full_text=full_text,
            gt_content=gt_content,
            gt_rules=gt_rules,
        )
        return doc

    async def generate_batch(self, count: int) -> list[GongWenDocument]:
        """Generate a batch of documents."""
        docs: list[GongWenDocument] = []
        topics = random.sample(TOPIC_POOL, min(count, len(TOPIC_POOL)))
        # Pad with random choices if count > pool size
        while len(topics) < count:
            topics.append(random.choice(TOPIC_POOL))

        for i, topic in enumerate(topics):
            print(f"\n📄 Generating document {i+1}/{count}")
            doc = await self.generate_one(topic)
            docs.append(doc)
            self._save_document(doc)

        return docs

    @staticmethod
    def _save_document(doc: GongWenDocument) -> None:
        path = GENERATED_DIR / f"{doc.doc_id}.json"
        path.write_text(
            json.dumps(doc.model_dump(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"  [gen] saved to {path.name}")


# ═══════════════════════════════════════════════════════════════════
#  Encoder (Phase 2 — dual-track extraction)
# ═══════════════════════════════════════════════════════════════════

class Encoder:
    """Extracts (content, rules) latent vectors from a full document."""

    def __init__(self, client: LLMClient) -> None:
        self.client = client

    async def encode_one(self, doc: GongWenDocument) -> EncodingResult:
        """Encode a single document into (content, rules) pair."""
        print(f"  [enc] encoding {doc.doc_id}...")

        # Parallel extraction — two independent LLM calls
        content_task = self.client.chat_json(
            system=ENCODE_CONTENT_SYSTEM,
            user=ENCODE_CONTENT_USER.format(document_text=doc.full_text),
            temperature=0.0,
        )
        rules_task = self.client.chat_json(
            system=ENCODE_RULES_SYSTEM,
            user=ENCODE_RULES_USER.format(document_text=doc.full_text),
            temperature=0.0,
        )

        content_dict, rules_dict = await asyncio.gather(content_task, rules_task)

        predicted_content = GongWenContent(**content_dict)
        predicted_rules = GongWenRules(**rules_dict)

        print(f"  [enc] content topic: {predicted_content.topic}")
        print(f"  [enc] rules: {predicted_rules.doc_type} / {predicted_rules.tone}")

        result = EncodingResult(
            doc_id=doc.doc_id,
            predicted_content=predicted_content,
            predicted_rules=predicted_rules,
        )
        self._save_result(result)
        return result

    async def encode_batch(self, docs: list[GongWenDocument]) -> list[EncodingResult]:
        """Encode a batch of documents."""
        results: list[EncodingResult] = []
        for i, doc in enumerate(docs):
            print(f"\n🔍 Encoding document {i+1}/{len(docs)}")
            result = await self.encode_one(doc)
            results.append(result)
        return results

    @staticmethod
    def _save_result(result: EncodingResult) -> None:
        path = ENCODED_DIR / f"{result.doc_id}.json"
        path.write_text(
            json.dumps(result.model_dump(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"  [enc] saved to {path.name}")


# ═══════════════════════════════════════════════════════════════════
#  Decoder (Phase 3 — reconstruct from latent vectors)
# ═══════════════════════════════════════════════════════════════════

class Decoder:
    """Reconstructs full documents from (content, rules) latent vectors."""

    def __init__(self, client: LLMClient) -> None:
        self.client = client
        self._rules_ref = _load_rules_reference()

    async def decode_one(self, encoding: EncodingResult) -> DecodingResult:
        """Reconstruct a single document from its encoding."""
        print(f"  [dec] decoding {encoding.doc_id}...")

        content_json = json.dumps(
            encoding.predicted_content.model_dump(), indent=2, ensure_ascii=False
        )
        rules_json = json.dumps(
            encoding.predicted_rules.model_dump(), indent=2, ensure_ascii=False
        )

        reconstructed_text = await self.client.chat(
            system=DECODE_DOCUMENT_SYSTEM.format(rules_reference=self._rules_ref),
            user=DECODE_DOCUMENT_USER.format(
                content_json=content_json,
                rules_json=rules_json,
            ),
            temperature=0.0,
        )

        print(f"  [dec] reconstructed ({len(reconstructed_text)} chars)")

        result = DecodingResult(
            doc_id=encoding.doc_id,
            reconstructed_text=reconstructed_text,
        )
        self._save_result(result)
        return result

    async def decode_batch(
        self, encodings: list[EncodingResult]
    ) -> list[DecodingResult]:
        """Decode a batch of encodings."""
        results: list[DecodingResult] = []
        for i, enc in enumerate(encodings):
            print(f"\n🔧 Decoding document {i+1}/{len(encodings)}")
            result = await self.decode_one(enc)
            results.append(result)
        return results

    @staticmethod
    def _save_result(result: DecodingResult) -> None:
        path = DECODED_DIR / f"{result.doc_id}.json"
        path.write_text(
            json.dumps(result.model_dump(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"  [dec] saved to {path.name}")


# ═══════════════════════════════════════════════════════════════════
#  DirectGenerator — Paper 2 baseline
# ═══════════════════════════════════════════════════════════════════

class DirectGenerator:
    """Baseline for Paper 2: directly generate a document from topic + rules (no AE)."""

    def __init__(self, client: LLMClient) -> None:
        self.client = client
        self._rules_ref = _load_rules_reference()

    async def generate_one(self, topic: str, rules: GongWenRules) -> str:
        """Generate a document directly from topic and rules, without going through AE."""
        print(f"  [direct] topic: {topic}")
        rules_json = json.dumps(rules.model_dump(), ensure_ascii=False, indent=2)

        text = await self.client.chat(
            system=DIRECT_GENERATE_SYSTEM.format(rules_reference=self._rules_ref),
            user=DIRECT_GENERATE_USER.format(topic=topic, rules_json=rules_json),
            temperature=TEMPERATURE_CREATIVE,
        )
        print(f"  [direct] generated ({len(text)} chars)")
        return text

    async def generate_batch(
        self, topics: list[str], rules_list: list[GongWenRules]
    ) -> list[str]:
        """Generate a batch of documents directly."""
        results: list[str] = []
        for i, (topic, rules) in enumerate(zip(topics, rules_list)):
            print(f"\n📝 Direct-generating document {i+1}/{len(topics)}")
            text = await self.generate_one(topic, rules)
            results.append(text)
        return results


# ═══════════════════════════════════════════════════════════════════
#  Evaluator (Phase 4 — 6-metric hybrid evaluation)
# ═══════════════════════════════════════════════════════════════════

class Evaluator:
    """Runs 6-metric evaluation on the encode-decode pipeline."""

    def __init__(self, client: LLMClient) -> None:
        self.client = client

    async def evaluate_one(
        self,
        doc: GongWenDocument,
        encoding: EncodingResult,
        decoding: DecodingResult,
    ) -> EvalResult:
        """Evaluate a single document through all 6 metrics."""
        print(f"  [eval] evaluating {doc.doc_id}...")
        details: dict = {}

        # 1. Rule Adherence (Regex)
        rule_adherence = self._check_rule_adherence(
            decoding.reconstructed_text, encoding.predicted_rules.model_dump()
        )
        details["rule_adherence"] = rule_adherence

        # 2. Structural Match (gt_rules vs predicted_rules)
        structural_match = self._check_structural_match(
            doc.gt_rules.model_dump(), encoding.predicted_rules.model_dump()
        )
        details["structural_match"] = structural_match

        # 3. Semantic Similarity (embedding: original vs reconstructed)
        emb_orig, emb_recon = await self.client.embed_batch(
            [doc.full_text, decoding.reconstructed_text]
        )
        semantic_similarity = LLMClient.cosine_similarity(emb_orig, emb_recon)
        details["semantic_similarity_raw"] = semantic_similarity

        # 4. Content Accuracy (embedding: gt_content vs predicted_content)
        gt_content_str = json.dumps(doc.gt_content.model_dump(), ensure_ascii=False)
        pred_content_str = json.dumps(encoding.predicted_content.model_dump(), ensure_ascii=False)
        emb_gt, emb_pred = await self.client.embed_batch(
            [gt_content_str, pred_content_str]
        )
        content_accuracy = LLMClient.cosine_similarity(emb_gt, emb_pred)
        details["content_accuracy_raw"] = content_accuracy

        # 5. Content Preservation (LLM Judge)
        preservation_score, preservation_reason = await self._judge_content_preservation(
            doc.full_text, decoding.reconstructed_text
        )
        details["content_preservation_reasoning"] = preservation_reason

        # 6. Format Compliance (LLM Judge)
        compliance_score, compliance_reason = await self._judge_format_compliance(
            decoding.reconstructed_text,
            json.dumps(encoding.predicted_rules.model_dump(), ensure_ascii=False),
        )
        details["format_compliance_reasoning"] = compliance_reason

        # Clamp cosine similarities to [0, 1] (floating point can exceed 1.0)
        semantic_similarity = max(0.0, min(1.0, semantic_similarity))
        content_accuracy = max(0.0, min(1.0, content_accuracy))

        scores = EvalScores(
            rule_adherence=rule_adherence["score"],
            structural_match=structural_match["score"],
            semantic_similarity=semantic_similarity,
            content_accuracy=content_accuracy,
            content_preservation=preservation_score / 5.0,  # normalize 1-5 → 0-1
            format_compliance=compliance_score / 5.0,
            weighted_total=self._compute_weighted_total(
                rule_adherence["score"],
                structural_match["score"],
                semantic_similarity,
                content_accuracy,
                preservation_score / 5.0,
                compliance_score / 5.0,
            ),
        )

        print(f"  [eval] weighted_total: {scores.weighted_total:.3f}")
        return EvalResult(doc_id=doc.doc_id, scores=scores, details=details)

    async def evaluate_batch(
        self,
        docs: list[GongWenDocument],
        encodings: list[EncodingResult],
        decodings: list[DecodingResult],
        *,
        output_dir: Path | None = None,
    ) -> list[EvalResult]:
        """Evaluate a batch and write CSV report.

        Args:
            output_dir: Directory for the CSV report. Defaults to RESULTS_DIR.
        """
        results: list[EvalResult] = []
        for i, (doc, enc, dec) in enumerate(zip(docs, encodings, decodings)):
            print(f"\n📊 Evaluating document {i+1}/{len(docs)}")
            result = await self.evaluate_one(doc, enc, dec)
            results.append(result)

        self._write_csv_report(results, output_dir=output_dir)
        self._print_summary(results)
        return results

    # ── Hard Metric 1: Rule Adherence ──────────────────────────────

    @staticmethod
    def _check_rule_adherence(text: str, rules: dict) -> dict:
        """Regex-based checks on the reconstructed text."""
        checks: dict[str, bool] = {}
        total = 0
        passed = 0

        # Check required sections
        for section in rules.get("required_sections", []):
            key = f"section_{section}"
            present = section in text
            checks[key] = present
            total += 1
            if present:
                passed += 1

        # Check date format (民國紀年)
        has_date = bool(re.search(r"中華民國\s*\d{2,3}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日", text))
        checks["date_format"] = has_date
        total += 1
        if has_date:
            passed += 1

        # Check document number format
        has_doc_number = bool(re.search(r"第\s*[\d\w]+(號|号)", text))
        checks["doc_number"] = has_doc_number
        total += 1
        if has_doc_number:
            passed += 1

        # Check terminology constraints
        for term in rules.get("terminology_constraints", []):
            key = f"term_{term}"
            present = term in text
            checks[key] = present
            total += 1
            if present:
                passed += 1

        # Check sender org
        sender = rules.get("sender_org", "")
        if sender:
            checks["sender_org"] = sender in text
            total += 1
            if sender in text:
                passed += 1

        score = passed / total if total > 0 else 0.0
        return {"score": score, "checks": checks, "passed": passed, "total": total}

    # ── Hard Metric 2: Structural Match ────────────────────────────

    @staticmethod
    def _check_structural_match(gt_rules: dict, pred_rules: dict) -> dict:
        """Compare gt_rules vs predicted_rules field by field."""
        fields_to_check = [
            "doc_type",
            "tone",
            "required_sections",
            "formality_level",
            "has_attachments",
            "speed_class",
        ]
        matches: dict[str, bool] = {}
        total = 0
        passed = 0

        for field in fields_to_check:
            gt_val = gt_rules.get(field)
            pred_val = pred_rules.get(field)
            if field == "required_sections":
                # Order-insensitive comparison
                match = set(gt_val or []) == set(pred_val or [])
            else:
                match = gt_val == pred_val
            matches[field] = match
            total += 1
            if match:
                passed += 1

        score = passed / total if total > 0 else 0.0
        return {"score": score, "matches": matches, "passed": passed, "total": total}

    # ── LLM Judge: Content Preservation ────────────────────────────

    async def _judge_content_preservation(
        self, original: str, reconstructed: str
    ) -> tuple[int, str]:
        """LLM judge for content preservation (1-5)."""
        resp = await self.client.chat_json(
            system=JUDGE_CONTENT_PRESERVATION_SYSTEM,
            user=JUDGE_CONTENT_PRESERVATION_USER.format(
                original_text=original,
                reconstructed_text=reconstructed,
            ),
        )
        score = max(1, min(5, int(resp.get("score", 3))))
        reasoning = resp.get("reasoning", "")
        print(f"  [eval] content_preservation: {score}/5")
        return score, reasoning

    # ── LLM Judge: Format Compliance ───────────────────────────────

    async def _judge_format_compliance(
        self, document_text: str, rules_json: str
    ) -> tuple[int, str]:
        """LLM judge for format compliance (1-5)."""
        resp = await self.client.chat_json(
            system=JUDGE_FORMAT_COMPLIANCE_SYSTEM,
            user=JUDGE_FORMAT_COMPLIANCE_USER.format(
                document_text=document_text,
                rules_json=rules_json,
            ),
        )
        score = max(1, min(5, int(resp.get("score", 3))))
        reasoning = resp.get("reasoning", "")
        print(f"  [eval] format_compliance: {score}/5")
        return score, reasoning

    # ── Weighted Total ─────────────────────────────────────────────

    @staticmethod
    def _compute_weighted_total(
        rule_adherence: float,
        structural_match: float,
        semantic_similarity: float,
        content_accuracy: float,
        content_preservation: float,
        format_compliance: float,
    ) -> float:
        w = EVAL_WEIGHTS
        return (
            w["rule_adherence"] * rule_adherence
            + w["structural_match"] * structural_match
            + w["semantic_similarity"] * semantic_similarity
            + w["content_accuracy"] * content_accuracy
            + w["content_preservation"] * content_preservation
            + w["format_compliance"] * format_compliance
        )

    # ── CSV Report ─────────────────────────────────────────────────

    @staticmethod
    def _write_csv_report(
        results: list[EvalResult],
        *,
        output_dir: Path | None = None,
    ) -> None:
        target_dir = output_dir or RESULTS_DIR
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / "eval_report.csv"
        fieldnames = [
            "doc_id",
            "rule_adherence",
            "structural_match",
            "semantic_similarity",
            "content_accuracy",
            "content_preservation",
            "format_compliance",
            "weighted_total",
        ]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in results:
                row = {"doc_id": r.doc_id}
                row.update(
                    {k: f"{v:.4f}" for k, v in r.scores.model_dump().items()}
                )
                writer.writerow(row)
        print(f"\n📝 Report saved to {path}")

    @staticmethod
    def _print_summary(results: list[EvalResult]) -> None:
        if not results:
            return
        print("\n" + "=" * 60)
        print("  EVALUATION SUMMARY")
        print("=" * 60)
        metrics = [
            "rule_adherence",
            "structural_match",
            "semantic_similarity",
            "content_accuracy",
            "content_preservation",
            "format_compliance",
            "weighted_total",
        ]
        for metric in metrics:
            values = [getattr(r.scores, metric) for r in results]
            avg = sum(values) / len(values)
            print(f"  {metric:25s}: {avg:.4f}  (n={len(values)})")
        print("=" * 60)
