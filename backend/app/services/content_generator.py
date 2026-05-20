from __future__ import annotations

from app.core.config import get_settings
from app.schemas.ai import ROOTELLECT_PRODUCTS


class ContentGenerator:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def generate(
        self,
        content_type: str,
        topic: str,
        product_focus: list[str] | None = None,
        tone: str = "premium_calm",
    ) -> dict:
        products = ", ".join(product_focus or ROOTELLECT_PRODUCTS[:4])
        system = (
            "You create premium wellness D2C marketing content for Rootellect. "
            "Tone: calm, science-backed, founder-led, non-spammy, no medical claims, no fake urgency."
        )
        user = (
            f"Create {content_type} content about: {topic}. "
            f"Product focus: {products}. Tone: {tone}. "
            "Return JSON with keys: title, hooks (array), body, cta, hashtags (array)."
        )

        if self.settings.openai_api_key:
            try:
                from openai import AsyncOpenAI

                client = AsyncOpenAI(api_key=self.settings.openai_api_key)
                response = await client.responses.create(
                    model=self.settings.openai_model,
                    input=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                )
                text = response.output_text or ""
                return {"content_type": content_type, "topic": topic, "raw": text, "mode": "openai"}
            except Exception as exc:
                return self._fallback(content_type, topic, products, error=str(exc))

        return self._fallback(content_type, topic, products)

    def _fallback(self, content_type: str, topic: str, products: str, error: str | None = None) -> dict:
        return {
            "content_type": content_type,
            "topic": topic,
            "mode": "fallback",
            "title": f"{topic.title()} — calm wellness angle",
            "hooks": [
                f"What most people miss about {topic}",
                f"A gentler way to think about {topic}",
            ],
            "body": (
                f"Educational {content_type} for {topic}. Focus on {products}. "
                "Invite comments with 'help' or 'details' for a private guide — no hard selling."
            ),
            "cta": "Comment 'details' and we'll share something genuinely helpful in your DMs.",
            "hashtags": ["#rootellect", "#wellness", "#calmwomen"],
            "error": error,
        }
