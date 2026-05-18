"""
Risk Engine — Modern Portfolio Theory (MPT) based analysis
Calculates allocation drift, concentration risk, and rebalancing signals.
"""
from typing import List
from decimal import Decimal
import numpy as np


class RiskEngine:
    DRIFT_THRESHOLD = 0.05  # 5% absolute drift triggers rebalancing

    def __init__(self, holdings):
        self.holdings = holdings

    def total_cost_basis(self) -> float:
        total = 0.0
        for h in self.holdings:
            if h.quantity and h.avg_cost:
                total += float(h.quantity) * float(h.avg_cost)
        return round(total, 2)

    def asset_allocation(self) -> dict:
        """Returns current allocation by asset type and symbol"""
        total = self.total_cost_basis()
        if total == 0:
            return {}

        by_type: dict[str, float] = {}
        by_symbol: dict[str, float] = {}

        for h in self.holdings:
            if h.quantity and h.avg_cost:
                value = float(h.quantity) * float(h.avg_cost)
                asset_type = h.asset_type or "other"
                by_type[asset_type] = by_type.get(asset_type, 0) + value
                by_symbol[h.symbol] = value

        return {
            "by_type": {k: round(v / total * 100, 2) for k, v in by_type.items()},
            "by_symbol": {k: round(v / total * 100, 2) for k, v in by_symbol.items()},
            "total_value": total,
        }

    def risk_metrics(self) -> dict:
        """Heuristic risk metrics without live prices"""
        holdings_with_targets = [h for h in self.holdings if h.target_weight is not None]

        if not holdings_with_targets:
            return {"concentration_risk": "unknown", "diversification_score": 0}

        # Herfindahl-Hirschman Index (HHI) for concentration
        total = self.total_cost_basis()
        weights = []
        for h in self.holdings:
            if h.quantity and h.avg_cost and total > 0:
                w = (float(h.quantity) * float(h.avg_cost)) / total
                weights.append(w)

        hhi = sum(w ** 2 for w in weights) if weights else 0

        # HHI: 1/n = perfectly diversified, 1.0 = single asset
        n = len(weights)
        min_hhi = 1 / n if n > 0 else 1
        diversification_score = round((1 - hhi) / (1 - min_hhi) * 100, 1) if n > 1 else 0

        concentration_risk = "low" if hhi < 0.15 else "medium" if hhi < 0.25 else "high"

        return {
            "hhi": round(hhi, 4),
            "concentration_risk": concentration_risk,
            "diversification_score": min(diversification_score, 100),
            "num_assets": n,
        }

    def needs_rebalancing(self) -> bool:
        """True if any holding drifts > DRIFT_THRESHOLD from its target"""
        total = self.total_cost_basis()
        if total == 0:
            return False

        holdings_with_targets = [h for h in self.holdings if h.target_weight is not None]
        if not holdings_with_targets:
            return False

        for h in holdings_with_targets:
            if h.quantity and h.avg_cost:
                current_weight = (float(h.quantity) * float(h.avg_cost)) / total
                drift = abs(current_weight - float(h.target_weight))
                if drift > self.DRIFT_THRESHOLD:
                    return True
        return False

    def rebalancing_trades(self) -> list[dict]:
        """Calculate buy/sell trades to restore target weights"""
        total = self.total_cost_basis()
        if total == 0:
            return []

        trades = []
        for h in self.holdings:
            if h.target_weight is None or not h.avg_cost or not h.quantity:
                continue

            current_value = float(h.quantity) * float(h.avg_cost)
            current_weight = current_value / total
            target_weight = float(h.target_weight)
            drift = current_weight - target_weight

            if abs(drift) > self.DRIFT_THRESHOLD:
                target_value = target_weight * total
                trade_value = target_value - current_value
                trade_qty = trade_value / float(h.avg_cost)

                trades.append({
                    "symbol": h.symbol,
                    "action": "buy" if trade_value > 0 else "sell",
                    "quantity": round(abs(trade_qty), 4),
                    "estimated_value": round(abs(trade_value), 2),
                    "current_weight_pct": round(current_weight * 100, 2),
                    "target_weight_pct": round(target_weight * 100, 2),
                    "drift_pct": round(drift * 100, 2),
                })

        return sorted(trades, key=lambda x: abs(x["drift_pct"]), reverse=True)
