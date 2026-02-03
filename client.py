"""Async OpenAI client wrapper with retry, JSON parsing, and embedding support."""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

import numpy as np
from dotenv import load_dotenv
from openai import AsyncOpenAI

from config import LLM_MODEL, EMBEDDING_MODEL, MAX_RETRIES, RETRY_DELAY

load_dotenv()


class LLMClient:
    """Thin wrapper around AsyncOpenAI for the gongwen_ae pipeline."""

    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # ── Chat Completion ────────────────────────────────────────────

    async def chat(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.0,
        model: str = LLM_MODEL,
        json_mode: bool = False,
    ) -> str:
        """Send a chat completion request and return the assistant message."""
        kwargs: dict[str, Any] = {
            "model": model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = await self._client.chat.completions.create(**kwargs)
                return resp.choices[0].message.content or ""
            except Exception as e:
                if attempt == MAX_RETRIES:
                    raise
                print(f"  [retry {attempt}/{MAX_RETRIES}] {e}")
                await asyncio.sleep(RETRY_DELAY * attempt)
        return ""  # unreachable

    async def chat_json(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.0,
        model: str = LLM_MODEL,
    ) -> dict:
        """Chat with JSON mode and parse the response."""
        raw = await self.chat(
            system, user, temperature=temperature, model=model, json_mode=True
        )
        return json.loads(raw)

    # ── Embeddings ─────────────────────────────────────────────────

    async def embed(self, text: str) -> np.ndarray:
        """Get embedding vector for a single text."""
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = await self._client.embeddings.create(
                    model=EMBEDDING_MODEL, input=text
                )
                return np.array(resp.data[0].embedding, dtype=np.float32)
            except Exception as e:
                if attempt == MAX_RETRIES:
                    raise
                print(f"  [embed retry {attempt}/{MAX_RETRIES}] {e}")
                await asyncio.sleep(RETRY_DELAY * attempt)
        return np.array([])  # unreachable

    async def embed_batch(self, texts: list[str]) -> list[np.ndarray]:
        """Get embeddings for multiple texts concurrently."""
        tasks = [self.embed(t) for t in texts]
        return await asyncio.gather(*tasks)

    @staticmethod
    def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))
