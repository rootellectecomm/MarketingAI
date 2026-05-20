from __future__ import annotations

import hashlib
import structlog

from app.core.config import get_settings

logger = structlog.get_logger(__name__)


class ChromaKnowledgeStore:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._client = None
        self._collection = None

    def _ensure_collection(self):
        if self._collection is not None:
            return self._collection
        try:
            import chromadb

            self._client = chromadb.HttpClient(
                host=self.settings.chroma_host,
                port=self.settings.chroma_port,
            )
            self._collection = self._client.get_or_create_collection(self.settings.chroma_collection)
            return self._collection
        except Exception as exc:
            logger.warning("chroma_unavailable", error=str(exc))
            return None

    def upsert_document(self, doc_id: str, title: str, category: str, content: str) -> bool:
        collection = self._ensure_collection()
        if collection is None:
            return False
        try:
            from openai import OpenAI

            if not self.settings.openai_api_key:
                return False
            client = OpenAI(api_key=self.settings.openai_api_key)
            text = f"{title}\n{category}\n{content}"
            embedding = client.embeddings.create(
                model=self.settings.openai_embedding_model,
                input=text[:8000],
            ).data[0].embedding
            collection.upsert(
                ids=[doc_id],
                documents=[text],
                metadatas=[{"title": title, "category": category}],
                embeddings=[embedding],
            )
            return True
        except Exception as exc:
            logger.warning("chroma_upsert_failed", doc_id=doc_id, error=str(exc))
            return False

    def query(self, query_text: str, limit: int = 4) -> list[tuple[str, str, str, float]]:
        collection = self._ensure_collection()
        if collection is None or not self.settings.openai_api_key:
            return []
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.settings.openai_api_key)
            embedding = client.embeddings.create(
                model=self.settings.openai_embedding_model,
                input=query_text[:2000],
            ).data[0].embedding
            results = collection.query(query_embeddings=[embedding], n_results=limit)
            documents = (results.get("documents") or [[]])[0]
            metadatas = (results.get("metadatas") or [[]])[0]
            distances = (results.get("distances") or [[]])[0]
            output: list[tuple[str, str, str, float]] = []
            for doc, meta, distance in zip(documents, metadatas, distances, strict=False):
                meta = meta or {}
                score = max(0.0, 1.0 - float(distance or 0))
                output.append((meta.get("title", "Knowledge"), meta.get("category", "general"), doc, score))
            return output
        except Exception as exc:
            logger.warning("chroma_query_failed", error=str(exc))
            return []

    @staticmethod
    def document_id(title: str, content: str) -> str:
        digest = hashlib.sha256(f"{title}:{content[:200]}".encode()).hexdigest()[:24]
        return f"doc-{digest}"
