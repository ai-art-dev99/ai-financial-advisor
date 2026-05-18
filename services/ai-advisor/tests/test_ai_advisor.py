"""
Unit tests for AI Advisor service.
No external API calls — everything mocked.
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ─── Prompt Builder Tests ──────────────────────────────────────

from llm.prompt_builder import build_system_prompt, SYSTEM_PERSONA


class TestPromptBuilder:
    def test_base_prompt_contains_persona(self):
        prompt = build_system_prompt()
        assert "Argo" in prompt
        assert "financial advisor" in prompt.lower()

    def test_risk_profile_injected(self):
        profile = {
            "risk_score": 7,
            "risk_category": "moderate",
            "investment_horizon": 60,
            "investable_assets": 50000,
            "monthly_income": 6000,
        }
        prompt = build_system_prompt(risk_profile=profile)
        assert "7/10" in prompt
        assert "moderate" in prompt
        assert "60 months" in prompt
        assert "$50,000" in prompt

    def test_portfolio_summary_injected(self):
        summary = {
            "total_cost_basis": 100000,
            "holdings_count": 5,
            "rebalancing_needed": True,
            "risk_metrics": {
                "concentration_risk": "medium",
                "diversification_score": 72.5,
            },
            "asset_allocation": {
                "by_type": {"stock": 60.0, "bond": 30.0, "cash": 10.0},
            },
        }
        prompt = build_system_prompt(portfolio_summary=summary)
        assert "$100,000" in prompt
        assert "⚠️ YES" in prompt          # rebalancing alert
        assert "medium" in prompt
        assert "72" in prompt              # diversification score

    def test_rag_context_appended(self):
        context = "<context>\n[Reference: MPT]\nModern Portfolio Theory...\n</context>"
        prompt = build_system_prompt(rag_context=context)
        assert "<context>" in prompt
        assert "Modern Portfolio Theory" in prompt

    def test_no_rebalancing_flag(self):
        summary = {
            "total_cost_basis": 50000,
            "holdings_count": 3,
            "rebalancing_needed": False,
            "risk_metrics": {"concentration_risk": "low", "diversification_score": 85},
            "asset_allocation": {"by_type": {}},
        }
        prompt = build_system_prompt(portfolio_summary=summary)
        assert "⚠️ YES" not in prompt
        assert "No" in prompt

    def test_empty_inputs_returns_base_prompt(self):
        prompt = build_system_prompt()
        assert SYSTEM_PERSONA in prompt


# ─── Conversation Manager Tests ────────────────────────────────

class TestConversationManager:
    """Tests using mocked Redis"""

    @pytest.fixture
    def mock_redis(self):
        r = AsyncMock()
        r.get = AsyncMock(return_value=None)
        r.set = AsyncMock(return_value=True)
        r.delete = AsyncMock(return_value=1)
        r.keys = AsyncMock(return_value=[])
        return r

    @pytest.fixture
    def manager(self, mock_redis):
        from conversation import ConversationManager
        mgr = ConversationManager()
        mgr._redis = mock_redis
        return mgr, mock_redis

    @pytest.mark.asyncio
    async def test_get_history_empty(self, manager):
        mgr, redis = manager
        redis.get.return_value = None
        history = await mgr.get_history("session-1")
        assert history == []

    @pytest.mark.asyncio
    async def test_get_history_returns_messages(self, manager):
        mgr, redis = manager
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        redis.get.return_value = json.dumps(messages)
        history = await mgr.get_history("session-1")
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["content"] == "Hi there!"

    @pytest.mark.asyncio
    async def test_append_messages(self, manager):
        mgr, redis = manager
        redis.get.return_value = None
        await mgr.append_messages("session-1", [
            {"role": "user", "content": "Tell me about ETFs"},
            {"role": "assistant", "content": "ETFs are..."},
        ])
        redis.set.assert_called_once()
        call_args = redis.set.call_args
        saved = json.loads(call_args[0][1])
        assert len(saved) == 2
        assert saved[0]["content"] == "Tell me about ETFs"

    @pytest.mark.asyncio
    async def test_history_rolling_window(self, manager):
        """History should be trimmed to max_history_messages"""
        from config import settings
        mgr, redis = manager
        # Existing history already at max
        existing = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"msg {i}"}
            for i in range(settings.max_history_messages)
        ]
        redis.get.return_value = json.dumps(existing)
        # Append 2 more
        await mgr.append_messages("session-1", [
            {"role": "user", "content": "new message"},
            {"role": "assistant", "content": "new reply"},
        ])
        saved = json.loads(redis.set.call_args[0][1])
        assert len(saved) <= settings.max_history_messages

    @pytest.mark.asyncio
    async def test_clear_session(self, manager):
        mgr, redis = manager
        await mgr.clear_session("session-1")
        redis.delete.assert_called_once_with("chat:session:session-1")


# ─── RAG Retriever Tests ───────────────────────────────────────

class TestRAGRetriever:
    @pytest.fixture
    def mock_collection(self):
        col = MagicMock()
        col.count.return_value = 5
        col.query.return_value = {
            "documents": [["ETFs provide diversification at low cost."]],
            "metadatas": [[{"title": "ETF Guide", "source": "knowledge_base"}]],
            "distances": [[0.3]],
        }
        return col

    def test_retrieve_returns_context_block(self, mock_collection):
        from rag.retriever import RAGRetriever
        retriever = RAGRetriever()
        with patch.object(retriever, "_get_client") as mock_client:
            mock_client.return_value.get_collection.return_value = mock_collection
            with patch.object(retriever, "_search_collection",
                              return_value=[{
                                  "content": "ETFs provide diversification.",
                                  "metadata": {"title": "ETF Guide"},
                                  "score": 0.8,
                              }]):
                context = retriever.retrieve("tell me about ETFs")
        assert "<context>" in context
        assert "ETF" in context
        assert "</context>" in context

    def test_retrieve_empty_when_no_results(self):
        from rag.retriever import RAGRetriever
        retriever = RAGRetriever()
        with patch.object(retriever, "_search_collection", return_value=[]):
            with patch.object(retriever, "_get_client"):
                context = retriever.retrieve("random unrelated query", user_id=None)
        assert context == ""

    def test_distance_threshold_filters_low_relevance(self):
        from rag.retriever import RAGRetriever
        retriever = RAGRetriever()
        mock_col = MagicMock()
        mock_col.count.return_value = 3
        mock_col.query.return_value = {
            "documents": [["Irrelevant content"]],
            "metadatas": [[{"title": "Irrelevant"}]],
            "distances": [[0.9]],  # high distance = low similarity
        }
        with patch.object(retriever, "_get_client") as mock_client:
            mock_client.return_value.get_collection.return_value = mock_col
            results = retriever._search_collection("financial query", "test_collection")
        # Should be filtered out (distance > 0.7 threshold)
        assert results == []


# ─── LLM Client Tests ─────────────────────────────────────────

class TestLLMClient:
    @pytest.mark.asyncio
    async def test_stream_yields_chunks(self):
        from llm.client import LLMClient
        client = LLMClient()

        async def mock_text_stream():
            for chunk in ["Hello", " there", "!"]:
                yield chunk

        mock_stream_ctx = AsyncMock()
        mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_stream_ctx)
        mock_stream_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_stream_ctx.text_stream = mock_text_stream()

        with patch.object(client._client.messages, "stream", return_value=mock_stream_ctx):
            chunks = []
            async for chunk in client.stream(
                messages=[{"role": "user", "content": "Hi"}],
                system_prompt="You are helpful",
            ):
                chunks.append(chunk)

        assert chunks == ["Hello", " there", "!"]

    @pytest.mark.asyncio
    async def test_stream_handles_error_gracefully(self):
        from llm.client import LLMClient
        client = LLMClient()

        with patch.object(client._client.messages, "stream", side_effect=Exception("API error")):
            chunks = []
            async for chunk in client.stream(
                messages=[{"role": "user", "content": "Hi"}],
                system_prompt="You are helpful",
            ):
                chunks.append(chunk)

        assert any("Error" in c for c in chunks)