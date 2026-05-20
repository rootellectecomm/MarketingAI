from __future__ import annotations

SEGMENT_KEYWORDS: dict[str, list[str]] = {
    "pcos": ["pcos", "irregular period", "hormonal imbalance", "androgen"],
    "stress_sleep": ["stress", "sleep", "anxiety", "calm", "restless", "insomnia"],
    "menopause": ["menopause", "perimenopause", "hot flash", "bone", "joint"],
    "energy_focus": ["energy", "fatigue", "tired", "focus", "brain fog"],
    "mood": ["mood", "low mood", "irritable", "emotional"],
    "general_wellness": ["help", "details", "wellness", "supplement", "vitamin"],
}


def detect_wellness_segment(text: str) -> str | None:
    lowered = text.lower()
    for segment, keywords in SEGMENT_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return segment
    return None
