from __future__ import annotations

import re

from app.models.enums import ModerationAction
from app.schemas.ai import ModerationResult

TOXIC_PATTERNS = [
    r"\b(kill|die|hate you|idiot|stupid|trash)\b",
    r"\b(abuse|harass|threat)\b",
]
SPAM_PATTERNS = [
    r"\b(bit\.ly|free followers|crypto|forex|telegram)\b",
    r"(.)\1{7,}",
]
MEDICAL_RISK_PATTERNS = [
    r"\b(cure|diagnose|treat my|medicine for|pregnant|breastfeeding)\b",
    r"\b(pcos cure|depression cure|menopause cure)\b",
]
PROMPT_INJECTION_PATTERNS = [
    r"\b(ignore previous|system prompt|developer message|jailbreak)\b",
]


def _matches(patterns: list[str], text: str) -> list[str]:
    return [pattern for pattern in patterns if re.search(pattern, text, re.IGNORECASE)]


class ModerationEngine:
    def evaluate(self, text: str) -> ModerationResult:
        flags: list[str] = []
        lowered = text.lower()

        if _matches(PROMPT_INJECTION_PATTERNS, lowered):
            flags.append("prompt_injection")
        if _matches(TOXIC_PATTERNS, lowered):
            flags.append("abuse")
        if _matches(SPAM_PATTERNS, lowered):
            flags.append("spam")
        if _matches(MEDICAL_RISK_PATTERNS, lowered):
            flags.append("medical_risk")
        if len(lowered.strip()) <= 1:
            flags.append("empty_or_too_short")

        if "abuse" in flags:
            return ModerationResult(
                action=ModerationAction.hide,
                flags=flags,
                confidence=0.9,
                notes="Toxic or abusive content should be hidden and logged.",
            )
        if "spam" in flags or "prompt_injection" in flags:
            return ModerationResult(
                action=ModerationAction.block,
                flags=flags,
                confidence=0.88,
                notes="Spam or prompt injection attempt blocked.",
            )
        if "medical_risk" in flags:
            return ModerationResult(
                action=ModerationAction.escalate,
                flags=flags,
                confidence=0.84,
                notes="Medical-risk language requires human-safe response rules.",
            )
        if flags:
            return ModerationResult(action=ModerationAction.escalate, flags=flags, confidence=0.7)
        return ModerationResult(action=ModerationAction.allow, flags=[], confidence=0.55)

