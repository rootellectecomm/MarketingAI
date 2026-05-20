from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.chroma_store import ChromaKnowledgeStore
from app.database.session import get_sessionmaker
from app.models.entities import KnowledgeDocument
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
        self.chroma = ChromaKnowledgeStore()

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

    async def _load_db_documents(self) -> list[RetrievedContext]:
        async with get_sessionmaker()() as session:
            result = await session.execute(
                select(KnowledgeDocument).where(KnowledgeDocument.is_active.is_(True)).order_by(KnowledgeDocument.updated_at.desc())
            )
            return [
                RetrievedContext(
                    title=item.title,
                    category=item.category,
                    content=item.content,
                    source=f"db:{item.id}",
                )
                for item in result.scalars().all()
            ]

    async def retrieve(self, query: str, limit: int = 4) -> list[RetrievedContext]:
        chroma_hits = self.chroma.query(query, limit=limit)
        if chroma_hits:
            return [
                RetrievedContext(title=title, category=category, content=content, score=score, source="chroma")
                for title, category, content, score in chroma_hits
            ]

        self.load_seed_documents()
        db_docs = await self._load_db_documents()
        corpus = self._documents + db_docs
        terms = {term.lower() for term in query.split() if len(term) > 2}
        ranked: list[RetrievedContext] = []
        for doc in corpus:
            haystack = f"{doc.title} {doc.category} {doc.content}".lower()
            score = sum(1 for term in terms if term in haystack)
            if score:
                ranked.append(doc.model_copy(update={"score": float(score)}))

        ranked.sort(key=lambda item: item.score, reverse=True)
        return ranked[:limit] or corpus[:limit]

    async def index_document(self, title: str, category: str, content: str, doc_id: str | None = None) -> bool:
        doc_id = doc_id or ChromaKnowledgeStore.document_id(title, content)
        return self.chroma.upsert_document(doc_id, title, category, content)
