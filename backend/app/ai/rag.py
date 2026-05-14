from __future__ import annotations

from pathlib import Path

from app.schemas.ai import RetrievedContext


def _default_seed_path() -> Path:
    candidates = [
        Path.cwd() / "seed" / "knowledge",
        Path.cwd().parent / "seed" / "knowledge",
        Path(__file__).resolve().parents[3] / "seed" / "knowledge",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


class RAGKnowledgeBase:
    def __init__(self, seed_path: Path | None = None) -> None:
        self.seed_path = seed_path or _default_seed_path()
        self._documents: list[RetrievedContext] = []
        self._loaded = False

    def load_seed_documents(self) -> None:
        if self._loaded:
            return
        if self.seed_path.exists():
            for path in self.seed_path.glob("*.md"):
                content = path.read_text(encoding="utf-8")
                title = path.stem.replace("-", " ").title()
                category = path.stem.split("-")[0]
                self._documents.append(
                    RetrievedContext(title=title, category=category, content=content, source=str(path))
                )
        self._loaded = True

    async def retrieve(self, query: str, limit: int = 4) -> list[RetrievedContext]:
        self.load_seed_documents()
        terms = {term.lower() for term in query.split() if len(term) > 2}
        ranked: list[RetrievedContext] = []
        for doc in self._documents:
            haystack = f"{doc.title} {doc.category} {doc.content}".lower()
            score = sum(1 for term in terms if term in haystack)
            if score:
                ranked.append(doc.model_copy(update={"score": float(score)}))

        ranked.sort(key=lambda item: item.score, reverse=True)
        return ranked[:limit] or self._documents[:limit]
