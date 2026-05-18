"""
Prompt Builder
Assembles the system prompt with:
  - AI advisor persona and guidelines
  - User's risk profile
  - Portfolio analysis
  - RAG context (news + knowledge base)
"""
from typing import Optional

SYSTEM_PERSONA = """\
You are Argo, an expert AI financial advisor built by a robo-advisory platform.
You provide personalised, actionable investment advice based on the user's risk profile, 
portfolio holdings, and current market conditions.

GUIDELINES:
- Always base advice on the user's specific portfolio and risk profile provided in context
- Be concise and clear — avoid jargon, explain terms when you use them
- When discussing specific stocks or ETFs, mention both upside potential and key risks
- Never guarantee returns — always frame advice probabilistically
- If the user asks about something outside your context, say so honestly
- Format numbers clearly: use $ for amounts, % for percentages
- When relevant, suggest rebalancing if portfolio drift is detected
- Keep responses focused: 2-4 paragraphs maximum unless the user asks for detail

IMPORTANT: You are not a licensed financial advisor. Always remind users to consult 
a licensed professional for major financial decisions.
"""


def build_system_prompt(
    risk_profile: Optional[dict] = None,
    portfolio_summary: Optional[dict] = None,
    rag_context: str = "",
) -> str:
    parts = [SYSTEM_PERSONA]

    # User risk profile section
    if risk_profile:
        score = risk_profile.get("risk_score", "unknown")
        category = risk_profile.get("risk_category", "unknown")
        horizon = risk_profile.get("investment_horizon", 0)
        assets = risk_profile.get("investable_assets", 0)
        parts.append(f"""
<user_profile>
Risk score: {score}/10 ({category})
Investment horizon: {horizon} months ({round(horizon/12, 1)} years)
Investable assets: ${assets:,.0f}
Monthly income: ${risk_profile.get('monthly_income', 0):,.0f}
</user_profile>""")

    # Portfolio summary section
    if portfolio_summary:
        rebalance = portfolio_summary.get("rebalancing_needed", False)
        total = portfolio_summary.get("total_cost_basis", 0)
        risk_metrics = portfolio_summary.get("risk_metrics", {})
        allocation = portfolio_summary.get("asset_allocation", {})
        by_type = allocation.get("by_type", {})

        alloc_str = ", ".join([f"{k}: {v:.1f}%" for k, v in by_type.items()])
        parts.append(f"""
<portfolio_status>
Total value: ${total:,.0f}
Holdings: {portfolio_summary.get('holdings_count', 0)} positions
Allocation: {alloc_str or 'not set'}
Concentration risk: {risk_metrics.get('concentration_risk', 'unknown')}
Diversification score: {risk_metrics.get('diversification_score', 0):.0f}/100
Rebalancing needed: {'⚠️ YES' if rebalance else 'No'}
</portfolio_status>""")

    # RAG context
    if rag_context:
        parts.append(f"\n{rag_context}")

    return "\n".join(parts)