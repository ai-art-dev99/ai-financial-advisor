"""
RAG Retriever
Searches ChromaDB collections for relevant context given a user query.
Returns merged, deduplicated results from news + knowledge base + portfolio.
"""
import logging
from typing import List
import chromadb
from chromadb.utils import embedding_functions

from config import settings
from rag.ingestor import NEWS_COLLECTION, KNOWLEDGE_COLLECTION, PORTFOLIO_COLLECTION

logger = logging.getLogger(__name__)


class RAGRetriever:
    def __init__(self):
        self._client: chromadb.Client | None = None
        self._ef = embedding_functions.DefaultEmbeddingFunction()

    def _get_client(self) -> chromadb.Client:
        if self._client is None:
            self._client = chromadb.HttpClient(
                host=settings.chroma_host,
                port=settings.chroma_port,
            )
        return self._client

    def _search_collection(self, collection_name: str, query: str, n: int = 3) -> List[dict]:
        try:
            client = self._get_client()
            col = client.get_collection(collection_name, embedding_function=self._ef)
            results = col.query(
                query_texts=[query],
                n_results=min(n, col.count()),
                include=["documents", "metadatas", "distances"],
            )
            docs = []
            for i, doc in enumerate(results["documents"][0]):
                distance = results["distances"][0][i]
                if distance < 0.7:  # cosine similarity threshold
                    docs.append({
                        "content": doc,
                        "metadata": results["metadatas"][0][i],
                        "score": 1 - distance,
                    })
            return docs
        except Exception as e:
            logger.warning(f"RAG search failed on {collection_name}: {e}")
            return []

    def retrieve(self, query: str, user_id: str | None = None) -> str:
        """
        Retrieve relevant context and format it as a string block
        to inject into the system prompt.
        """
        all_docs = []

        # 1. Knowledge base (financial theory)
        kb_docs = self._search_collection(KNOWLEDGE_COLLECTION, query, n=3)
        all_docs.extend([{"source": "knowledge", **d} for d in kb_docs])

        # 2. Recent news
        news_docs = self._search_collection(NEWS_COLLECTION, query, n=3)
        all_docs.extend([{"source": "news", **d} for d in news_docs])

        # 3. User's portfolio context (if available)
        if user_id:
            try:
                client = self._get_client()
                col = client.get_collection(PORTFOLIO_COLLECTION)
                result = col.get(ids=[f"portfolio_{user_id}"], include=["documents"])
                if result["documents"]:
                    all_docs.append({
                        "source": "portfolio",
                        "content": result["documents"][0],
                        "score": 1.0,
                    })
            except Exception:
                pass

        if not all_docs:
            return ""

        # Sort by relevance score
        all_docs.sort(key=lambda x: x.get("score", 0), reverse=True)
        top_docs = all_docs[:settings.rag_top_k]

        # Format context block
        context_parts = ["<context>"]
        for doc in top_docs:
            source = doc["source"]
            meta = doc.get("metadata", {})
            if source == "news":
                title = meta.get("title", "News")
                context_parts.append(f"[News: {title}]\n{doc['content']}")
            elif source == "knowledge":
                title = meta.get("title", "Reference")
                context_parts.append(f"[Reference: {title}]\n{doc['content']}")
            elif source == "portfolio":
                context_parts.append(f"[Your Portfolio]\n{doc['content']}")

        context_parts.append("</context>")
        return "\n\n".join(context_parts)


rag_retriever = RAGRetriever()