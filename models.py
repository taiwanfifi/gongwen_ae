"""Pydantic models for the gongwen_ae pipeline.

Latent Space Design:
- Content (Payload): Pure information JSON, NO official document jargon.
  If the content contains terms like 茲因、擬請、鈞鑒 → extraction failed.
- Rules (Style): Parameterized formatting settings that fully describe
  how to render content into a formal Taiwanese government document.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ── Content: the "semantic payload" ───────────────────────────────

class GongWenContent(BaseModel):
    """De-officialized pure information extracted from a document.

    This must read like a plain-language briefing, NOT a government document.
    Forbidden tokens: 茲、擬、鈞、惠、爰、敬陳、諒達、奉、准、據 (as引敘語).
    """

    topic: str = Field(description="One-line topic summary in plain language")
    intent: str = Field(description="What the sender wants to achieve (plain language)")
    key_events: list[str] = Field(
        default_factory=list,
        description="Chronological list of key facts / events",
    )
    entities: list[str] = Field(
        default_factory=list,
        description="People, organizations, locations, dates involved",
    )
    action_items: list[str] = Field(
        default_factory=list,
        description="Concrete actions requested or proposed",
    )
    background: str = Field(default="", description="Additional context if needed")


# ── Rules: the "style parameters" ─────────────────────────────────

class GongWenRules(BaseModel):
    """Parameterized formatting / style configuration."""

    doc_type: Literal["函", "公告", "書函", "簽", "令"] = Field(
        description="Document type"
    )
    sender_org: str = Field(description="Sending organization full name")
    receiver_org: str = Field(default="", description="Receiving organization (empty for 公告/簽)")
    tone: Literal["上行", "平行", "下行"] = Field(
        description="Tone direction: 上行(to superior), 平行(peer), 下行(to subordinate)"
    )
    required_sections: list[str] = Field(
        description="Ordered list of required sections, e.g. ['主旨','說明','辦法']"
    )
    formality_level: Literal["高", "中"] = Field(
        default="高", description="Formality level"
    )
    terminology_constraints: list[str] = Field(
        default_factory=list,
        description="Specific terms or phrases that MUST appear",
    )
    has_attachments: bool = Field(default=False, description="Whether attachments are referenced")
    speed_class: Literal["最速件", "速件", "普通件"] = Field(default="普通件")


# ── Full Document ──────────────────────────────────────────────────

class GongWenDocument(BaseModel):
    """A complete document bundled with its ground-truth latent vectors."""

    doc_id: str = Field(description="Unique document identifier")
    full_text: str = Field(description="The complete official document text")
    gt_content: GongWenContent = Field(description="Ground-truth content (payload)")
    gt_rules: GongWenRules = Field(description="Ground-truth rules (style)")


# ── Pipeline Results ───────────────────────────────────────────────

class EncodingResult(BaseModel):
    """Output of the encoder: predicted content + rules."""

    doc_id: str
    predicted_content: GongWenContent
    predicted_rules: GongWenRules


class DecodingResult(BaseModel):
    """Output of the decoder: reconstructed document."""

    doc_id: str
    reconstructed_text: str


class EvalScores(BaseModel):
    """Individual evaluation scores for one document."""

    rule_adherence: float = Field(ge=0, le=1, description="Regex-based rule check")
    structural_match: float = Field(ge=0, le=1, description="gt_rules vs predicted_rules match")
    semantic_similarity: float = Field(ge=0, le=1, description="Embedding cosine: original vs reconstructed")
    content_accuracy: float = Field(ge=0, le=1, description="Embedding cosine: gt_content vs predicted_content")
    content_preservation: float = Field(ge=0, le=1, description="LLM judge 1-5 normalized to 0-1")
    format_compliance: float = Field(ge=0, le=1, description="LLM judge 1-5 normalized to 0-1")
    weighted_total: float = Field(ge=0, le=1, description="Weighted aggregate score")


class EvalResult(BaseModel):
    """Full evaluation result for one document."""

    doc_id: str
    scores: EvalScores
    details: dict = Field(default_factory=dict, description="Per-metric details / explanations")
