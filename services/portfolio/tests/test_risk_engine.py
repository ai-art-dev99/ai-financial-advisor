import pytest

pytestmark = pytest.mark.asyncio


# ─── Portfolios CRUD ───────────────────────────────────────────

class TestPortfolios:
    async def test_create_portfolio(self, client):
        resp = await client.post("/portfolios/", json={
            "name": "Growth Portfolio",
            "currency": "USD",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Growth Portfolio"
        assert data["currency"] == "USD"
        assert data["is_active"] is True
        assert "id" in data

    async def test_list_portfolios_empty(self, client):
        resp = await client.get("/portfolios/")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_portfolios(self, client, portfolio):
        resp = await client.get("/portfolios/")
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["id"] == portfolio["id"]

    async def test_get_portfolio(self, client, portfolio):
        resp = await client.get(f"/portfolios/{portfolio['id']}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Test Portfolio"

    async def test_get_portfolio_not_found(self, client):
        resp = await client.get("/portfolios/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404

    async def test_delete_portfolio(self, client, portfolio):
        resp = await client.delete(f"/portfolios/{portfolio['id']}")
        assert resp.status_code == 204
        # Should not appear in list anymore
        list_resp = await client.get("/portfolios/")
        assert list_resp.json() == []

    async def test_multiple_portfolios(self, client):
        for name in ["Alpha", "Beta", "Gamma"]:
            await client.post("/portfolios/", json={"name": name})
        resp = await client.get("/portfolios/")
        assert len(resp.json()) == 3


# ─── Holdings ──────────────────────────────────────────────────

class TestHoldings:
    async def test_add_holding(self, client, portfolio):
        pid = portfolio["id"]
        resp = await client.post(f"/holdings/{pid}/holdings", json={
            "portfolio_id": pid,
            "symbol": "aapl",  # test lowercase normalization
            "asset_type": "stock",
            "quantity": 10,
            "avg_cost": 150.00,
            "target_weight": 0.25,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["symbol"] == "AAPL"  # uppercased
        assert float(data["quantity"]) == 10.0
        assert float(data["avg_cost"]) == 150.0

    async def test_add_holding_upsert_increases_quantity(self, client, portfolio):
        pid = portfolio["id"]
        payload = {"portfolio_id": pid, "symbol": "MSFT", "asset_type": "stock",
                   "quantity": 5, "avg_cost": 400.0}
        await client.post(f"/holdings/{pid}/holdings", json=payload)
        await client.post(f"/holdings/{pid}/holdings", json=payload)  # buy more
        resp = await client.get(f"/holdings/{pid}/holdings")
        holdings = resp.json()
        assert len(holdings) == 1  # not duplicated
        assert float(holdings[0]["quantity"]) == 10.0  # 5 + 5

    async def test_weighted_avg_cost_on_upsert(self, client, portfolio):
        pid = portfolio["id"]
        # Buy 10 @ $100 = $1000
        await client.post(f"/holdings/{pid}/holdings", json={
            "portfolio_id": pid, "symbol": "TSLA", "quantity": 10, "avg_cost": 100.0
        })
        # Buy 10 @ $200 = $2000 → total 20 @ $150 avg
        await client.post(f"/holdings/{pid}/holdings", json={
            "portfolio_id": pid, "symbol": "TSLA", "quantity": 10, "avg_cost": 200.0
        })
        resp = await client.get(f"/holdings/{pid}/holdings")
        holding = resp.json()[0]
        assert float(holding["avg_cost"]) == pytest.approx(150.0, rel=1e-2)

    async def test_get_holdings_wrong_portfolio(self, client):
        resp = await client.get("/holdings/00000000-0000-0000-0000-000000000000/holdings")
        assert resp.status_code == 404

    async def test_portfolio_analysis(self, client, portfolio):
        pid = portfolio["id"]
        for sym, qty, cost, weight in [
            ("SPY", 10, 530.0, 0.50),
            ("TLT", 20, 95.0,  0.30),
            ("GLD", 5,  185.0, 0.20),
        ]:
            await client.post(f"/holdings/{pid}/holdings", json={
                "portfolio_id": pid, "symbol": sym,
                "quantity": qty, "avg_cost": cost, "target_weight": weight
            })
        resp = await client.get(f"/holdings/{pid}/analysis")
        assert resp.status_code == 200
        data = resp.json()
        assert data["holdings_count"] == 3
        assert data["total_cost_basis"] > 0
        assert "hhi" in data["risk_metrics"]
        assert "diversification_score" in data["risk_metrics"]
        assert isinstance(data["rebalancing_needed"], bool)


# ─── Transactions ──────────────────────────────────────────────

class TestTransactions:
    async def test_record_buy_transaction(self, client, portfolio):
        pid = portfolio["id"]
        # First add a holding
        await client.post(f"/holdings/{pid}/holdings", json={
            "portfolio_id": pid, "symbol": "NVDA", "quantity": 5, "avg_cost": 800.0
        })
        resp = await client.post(f"/transactions/{pid}/transactions", json={
            "portfolio_id": pid,
            "symbol": "NVDA",
            "tx_type": "buy",
            "quantity": 2,
            "price": 820.0,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["tx_type"] == "buy"
        assert float(data["total_amount"]) == pytest.approx(1640.0)

    async def test_record_sell_reduces_quantity(self, client, portfolio):
        pid = portfolio["id"]
        await client.post(f"/holdings/{pid}/holdings", json={
            "portfolio_id": pid, "symbol": "AAPL", "quantity": 10, "avg_cost": 190.0
        })
        await client.post(f"/transactions/{pid}/transactions", json={
            "portfolio_id": pid, "symbol": "AAPL", "tx_type": "sell",
            "quantity": 3, "price": 200.0,
        })
        resp = await client.get(f"/holdings/{pid}/holdings")
        holding = next(h for h in resp.json() if h["symbol"] == "AAPL")
        assert float(holding["quantity"]) == 7.0

    async def test_sell_more_than_owned_fails(self, client, portfolio):
        pid = portfolio["id"]
        await client.post(f"/holdings/{pid}/holdings", json={
            "portfolio_id": pid, "symbol": "GOOG", "quantity": 2, "avg_cost": 170.0
        })
        resp = await client.post(f"/transactions/{pid}/transactions", json={
            "portfolio_id": pid, "symbol": "GOOG", "tx_type": "sell",
            "quantity": 100, "price": 170.0,
        })
        assert resp.status_code == 400
        assert "Insufficient" in resp.json()["detail"]

    async def test_list_transactions(self, client, portfolio):
        pid = portfolio["id"]
        await client.post(f"/holdings/{pid}/holdings", json={
            "portfolio_id": pid, "symbol": "SPY", "quantity": 10, "avg_cost": 530.0
        })
        for _ in range(3):
            await client.post(f"/transactions/{pid}/transactions", json={
                "portfolio_id": pid, "symbol": "SPY", "tx_type": "buy",
                "quantity": 1, "price": 530.0,
            })
        resp = await client.get(f"/transactions/{pid}/transactions")
        assert resp.status_code == 200
        assert len(resp.json()) == 3


# ─── Performance ───────────────────────────────────────────────

class TestPerformance:
    async def test_summary_empty_portfolio(self, client, portfolio):
        pid = portfolio["id"]
        resp = await client.get(f"/performance/{pid}/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["snapshots_count"] == 0
        assert data["latest_value"] is None

    async def test_snapshots_empty(self, client, portfolio):
        pid = portfolio["id"]
        resp = await client.get(f"/performance/{pid}/snapshots")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_wrong_portfolio_summary(self, client):
        resp = await client.get("/performance/00000000-0000-0000-0000-000000000000/summary")
        assert resp.status_code == 404