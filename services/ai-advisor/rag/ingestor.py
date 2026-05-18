"""
Document Ingestor
Fetches financial news, documents, and knowledge base items
and stores them as vector embeddings in ChromaDB.
"""
import asyncio
import hashlib
import logging
from datetime import datetime, timezone
from typing import List

import feedparser
import httpx
import chromadb
from chromadb.utils import embedding_functions

from config import settings

logger = logging.getLogger(__name__)

# Collections
NEWS_COLLECTION = "financial_news"
KNOWLEDGE_COLLECTION = "financial_knowledge"
PORTFOLIO_COLLECTION = "portfolio_context"

# Financial knowledge base articles (seeded on startup)
KNOWLEDGE_BASE = [
    {
        "id": "kb_001",
        "title": "Modern Portfolio Theory",
        "content": """Modern Portfolio Theory (MPT), developed by Harry Markowitz, shows how investors can construct portfolios to maximize expected return for a given level of risk. The key insight is diversification: combining assets with low correlation reduces portfolio volatility without necessarily reducing returns. The efficient frontier represents the set of portfolios offering the highest expected return for each level of risk. MPT uses mean-variance optimization where portfolio return is the weighted sum of individual returns, and portfolio variance depends on both individual variances and covariances between assets.""",
    },
    {
        "id": "kb_002",
        "title": "Asset Allocation Strategies",
        "content": """Asset allocation is the process of dividing investments among different asset categories: stocks, bonds, real estate, and cash equivalents. Strategic allocation sets long-term targets based on risk tolerance and investment horizon. Tactical allocation allows short-term deviations to exploit market opportunities. Common guidelines: conservative investors (30-40% stocks, 60-70% bonds), moderate investors (60% stocks, 40% bonds), aggressive investors (80-90% stocks, 10-20% bonds). Rebalancing restores target allocations when drift exceeds thresholds (typically 5%).""",
    },
    {
        "id": "kb_003",
        "title": "Risk Management in Investing",
        "content": """Investment risk takes many forms: market risk (systematic), company-specific risk (unsystematic), liquidity risk, inflation risk, and sequence-of-returns risk. Diversification eliminates unsystematic risk. Key metrics: Standard deviation measures volatility. Beta measures sensitivity to market moves. Sharpe ratio measures risk-adjusted return (excess return per unit of volatility). Maximum drawdown shows the largest peak-to-trough decline. Value at Risk (VaR) estimates potential losses at a given confidence level.""",
    },
    {
        "id": "kb_004",
        "title": "ETFs vs Individual Stocks",
        "content": """Exchange-Traded Funds (ETFs) offer instant diversification, low expense ratios, and tax efficiency. Index ETFs like SPY (S&P 500) and QQQ (Nasdaq 100) provide broad market exposure. Individual stocks offer potential for higher returns but carry concentration risk. A core-satellite approach uses ETFs as the core (70-80%) with individual stocks as satellites (20-30%). For most retail investors, low-cost index ETFs outperform active stock picking after fees and taxes.""",
    },
    {
        "id": "kb_005",
        "title": "Dollar Cost Averaging",
        "content": """Dollar Cost Averaging (DCA) involves investing a fixed amount at regular intervals regardless of market conditions. Benefits: reduces impact of volatility, removes emotion from investment decisions, lowers average cost per share in declining markets. Example: investing $500 monthly buys more shares when prices are low and fewer when high. Research shows DCA underperforms lump-sum investing when markets trend upward (as they historically do ~75% of the time), but reduces risk for investors who cannot tolerate potential short-term losses.""",
    },
    {
        "id": "kb_006",
        "title": "Rebalancing Strategies",
        "content": """Portfolio rebalancing restores target asset allocations after market drift. Three main approaches: calendar rebalancing (quarterly or annually), threshold rebalancing (when any asset drifts beyond 5% from target), and tactical rebalancing (opportunistic during market dislocations). Tax-efficient rebalancing uses new contributions, dividend reinvestment, and tax-loss harvesting to minimize taxable events. Studies show annual or threshold rebalancing at 5% produces similar returns to more frequent rebalancing but with lower transaction costs.""",
    },
]

# Free RSS feeds for financial news
NEWS_FEEDS = [
    "https://feeds.finance.yahoo.com/rss/2.0/headline",
    "https://www.marketwatch.com/rss/topstories",
    "https://feeds.bloomberg.com/markets/news.rss",
]


def _chunk_text(text: str, size: int = 800, overlap: int = 100) -> List[str]:
    """Split text into overlapping chunks."""
    if len(text) <= size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(text[start:end])
        start += size - overlap
    return chunks


def _doc_id(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


class DocumentIngestor:
    def __init__(self):
        self._client: chromadb.AsyncClientAPI | None = None
        self._ef = embedding_functions.DefaultEmbeddingFunction()

    def _get_client(self) -> chromadb.Client:
        if self._client is None:
            self._client = chromadb.HttpClient(
                host=settings.chroma_host,
                port=settings.chroma_port,
            )
        return self._client

    async def ensure_collections(self):
        """Create collections on startup if they don't exist."""
        try:
            client = self._get_client()
            for name in [NEWS_COLLECTION, KNOWLEDGE_COLLECTION, PORTFOLIO_COLLECTION]:
                client.get_or_create_collection(
                    name=name,
                    embedding_function=self._ef,
                    metadata={"hnsw:space": "cosine"},
                )
            # Seed knowledge base
            await self.ingest_knowledge_base()
            logger.info("ChromaDB collections ready")
        except Exception as e:
            logger.warning(f"ChromaDB not available: {e} — RAG will be disabled")

    async def ingest_knowledge_base(self):
        """Seed static financial knowledge into ChromaDB."""
        try:
            client = self._get_client()
            col = client.get_collection(KNOWLEDGE_COLLECTION)

            for doc in KNOWLEDGE_BASE:
                chunks = _chunk_text(doc["content"], settings.rag_chunk_size, settings.rag_chunk_overlap)
                for i, chunk in enumerate(chunks):
                    chunk_id = f"{doc['id']}_chunk_{i}"
                    existing = col.get(ids=[chunk_id])
                    if not existing["ids"]:
                        col.add(
                            ids=[chunk_id],
                            documents=[chunk],
                            metadatas=[{"title": doc["title"], "source": "knowledge_base", "chunk": i}],
                        )
        except Exception as e:
            logger.warning(f"Knowledge base ingestion failed: {e}")

    async def ingest_news(self):
        """Fetch and store latest financial news from RSS feeds."""
        try:
            client = self._get_client()
            col = client.get_collection(NEWS_COLLECTION)
            ingested = 0

            async with httpx.AsyncClient(timeout=10) as http:
                for feed_url in NEWS_FEEDS:
                    try:
                        resp = await http.get(feed_url)
                        feed = feedparser.parse(resp.text)
                        for entry in feed.entries[:10]:
                            content = f"{entry.get('title', '')}. {entry.get('summary', '')}"
                            doc_id = _doc_id(content)
                            existing = col.get(ids=[doc_id])
                            if not existing["ids"]:
                                col.add(
                                    ids=[doc_id],
                                    documents=[content],
                                    metadatas=[{
                                        "title": entry.get("title", ""),
                                        "source": feed_url,
                                        "published": entry.get("published", ""),
                                        "link": entry.get("link", ""),
                                    }],
                                )
                                ingested += 1
                    except Exception as e:
                        logger.warning(f"Feed {feed_url} failed: {e}")

            logger.info(f"Ingested {ingested} news articles")
            return ingested
        except Exception as e:
            logger.error(f"News ingestion failed: {e}")
            return 0

    async def ingest_portfolio_snapshot(self, user_id: str, holdings: list, analysis: dict):
        """Store user portfolio data for personalised RAG context."""
        try:
            client = self._get_client()
            col = client.get_collection(PORTFOLIO_COLLECTION)

            holdings_text = "\n".join([
                f"{h['symbol']}: {h['quantity']} shares @ avg ${h.get('avg_cost', 0):.2f} "
                f"(weight: {h.get('target_weight', 0)*100:.1f}%)"
                for h in holdings
            ])
            risk_text = (
                f"Concentration risk: {analysis.get('risk_metrics', {}).get('concentration_risk', 'unknown')}. "
                f"Diversification score: {analysis.get('risk_metrics', {}).get('diversification_score', 0):.1f}/100. "
                f"Rebalancing needed: {analysis.get('rebalancing_needed', False)}."
            )
            content = f"Portfolio snapshot for {user_id}:\n{holdings_text}\n{risk_text}"
            doc_id = f"portfolio_{user_id}"

            col.upsert(
                ids=[doc_id],
                documents=[content],
                metadatas=[{"user_id": user_id, "type": "portfolio_snapshot", "updated": datetime.now(timezone.utc).isoformat()}],
            )
        except Exception as e:
            logger.warning(f"Portfolio snapshot ingestion failed: {e}")