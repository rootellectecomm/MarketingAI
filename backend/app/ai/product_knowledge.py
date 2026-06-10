from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RootellectProduct:
    name: str
    url: str
    format: str
    dosage: str
    positioning: str
    best_for: tuple[str, ...]
    key_ingredients: tuple[str, ...]
    triggers: tuple[str, ...]
    intent_key: str


ROOTELLECT_PRODUCT_CATALOG: dict[str, RootellectProduct] = {
    "Mind Calm": RootellectProduct(
        name="Mind Calm",
        url="https://www.rootellect.com/products/mind-calm",
        format="Vegan capsules",
        dosage="1 capsule after dinner or at night",
        positioning="Non-melatonin, non-sedative calm, sleep and mental clarity support.",
        best_for=(
            "overthinking",
            "stress",
            "mental fatigue",
            "brain fog",
            "difficulty switching off",
            "poor sleep quality",
            "next-day mental freshness",
        ),
        key_ingredients=("B-LIT Bacopa / Bacopa monnieri 300 mg", "Jatamansi", "L-Theanine", "Stinging Nettle"),
        triggers=(
            "stress",
            "overthinking",
            "poor sleep",
            "mind active",
            "active at night",
            "can't sleep",
            "cant sleep",
            "sleep",
            "neend",
            "raat",
            "brain fog",
            "focus",
            "burnout",
            "mental fatigue",
            "tired brain",
        ),
        intent_key="stress_sleep",
    ),
    "Women Balance": RootellectProduct(
        name="Women Balance",
        url="https://www.rootellect.com/products/women-balance",
        format="Vegan capsules",
        dosage="2 capsules daily",
        positioning="Daily women's hormonal wellness, energy, PMS and mood support.",
        best_for=(
            "PMS discomfort",
            "low energy",
            "mood swings",
            "monthly fatigue",
            "daily hormonal balance",
            "general women's wellness",
        ),
        key_ingredients=(
            "Moringa",
            "KSM-66 Ashwagandha",
            "Shatavari",
            "Punarnava",
            "Ferrous Bisglycinate",
            "Beta-Carotene",
            "Vegan Vitamin D3",
            "Vitamin B6 P-5-P",
            "L-5-MTHF",
        ),
        triggers=(
            "pms",
            "period",
            "periods",
            "monthly",
            "fatigue before periods",
            "period fatigue",
            "low energy",
            "weakness",
            "mood swings",
            "women supplement",
            "daily women",
        ),
        intent_key="pms_energy",
    ),
    "PCOS Support": RootellectProduct(
        name="PCOS Support",
        url="https://www.rootellect.com/products/pcos-pcod-support",
        format="Tablets",
        dosage="1 tablet twice daily / 2 tablets daily",
        positioning="Non-hormonal, multi-pathway PCOS/PCOD wellness support.",
        best_for=(
            "cycle regularity support",
            "hormonal wellness",
            "acne or oily skin linked with hormonal imbalance",
            "cravings and bloating",
            "unwanted facial hair support",
            "metabolic wellness",
            "stress-related hormonal imbalance",
        ),
        key_ingredients=(
            "Shatavari",
            "Vitex",
            "Ashoka",
            "Berberis aristata",
            "Spearmint extract",
            "Shivlingi",
            "Lodhra",
            "Curcumin",
            "Ashwagandha",
            "Triphala",
            "Piperine",
        ),
        triggers=(
            "pcos",
            "pcod",
            "irregular periods",
            "irregular cycle",
            "cycle issue",
            "acne",
            "facial hair",
            "oily skin",
            "cravings",
            "bloating",
            "hormonal imbalance",
        ),
        intent_key="pcos_pcod",
    ),
    "Perimenopause Support": RootellectProduct(
        name="Perimenopause Support",
        url="https://www.rootellect.com/products/perimenopause-support",
        format="Tablets",
        dosage="2 tablets daily",
        positioning="35+ transition wellness support.",
        best_for=(
            "mood changes",
            "hot flashes",
            "sleep disturbance",
            "hormonal transition",
            "energy changes",
            "bone and nutrient support",
            "calmness during transition years",
        ),
        key_ingredients=(
            "Shatavari",
            "Black Cohosh",
            "Ashwagandha",
            "Jatamansi",
            "Vitex",
            "Myo-Inositol",
            "Milk Thistle",
            "Vegan D3",
            "Magnesium Glycinate",
            "Curcumin",
            "Calcium D-Glucarate",
            "Broccoli Seed",
            "B6",
            "Folate",
            "B12",
            "Zinc",
        ),
        triggers=(
            "35+",
            "perimenopause",
            "menopause",
            "hot flash",
            "hot flashes",
            "transition",
            "mom",
            "mother",
            "mummy",
            "sleep changes",
            "mood shifts",
        ),
        intent_key="perimenopause",
    ),
}

ROOTELLECT_PRODUCTS = list(ROOTELLECT_PRODUCT_CATALOG)

RED_FLAG_TERMS = (
    "pregnant",
    "pregnancy",
    "breastfeeding",
    "medicine",
    "medication",
    "diagnose",
    "severe",
    "bleeding",
    "chest pain",
    "suicidal",
    "self harm",
    "allergic",
    "adverse",
)

CURE_CLAIM_TERMS = ("cure", "treat", "reverse", "guarantee", "permanent")

HINGLISH_MARKERS = (
    "hai",
    "hain",
    "hota",
    "hoti",
    "bahut",
    "raat",
    "neend",
    "mom ko",
    "ke time",
    "ka",
    "ki",
    "me",
)


def is_hinglish(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in HINGLISH_MARKERS)


def route_product(text: str) -> RootellectProduct | None:
    lowered = text.lower()
    priority = ("PCOS Support", "Perimenopause Support", "Women Balance", "Mind Calm")
    for product_name in priority:
        product = ROOTELLECT_PRODUCT_CATALOG[product_name]
        if product.name.lower() in lowered or any(trigger in lowered for trigger in product.triggers):
            return product
    return None


def knowledge_source(retrieved_sources: list[str]) -> str:
    if retrieved_sources:
        return retrieved_sources[0]
    return "structured_product_catalog"
