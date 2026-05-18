"""
Portfolio Context Fetcher
Calls the portfolio service to get live holdings and analysis
for the authenticated user, then formats them for the prompt.
"""
import logging
import httpx
from typing import Optional
from config import settings

logger = logging.getLogger(__name__)


async def fetch_portfolio_context(
    user_id: str,
    access_token: str,
) -> tuple[Optional[dict], Optional[dict]]:
    """
    Returns (portfolio_summary, risk_profile) for the user.
    Both can be None if the service is unavailable or user has no portfolio.
    """
    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient(timeout=5.0) as client:
        portfolio_summary = None
        risk_profile = None

        # 1. Get risk profile
        try:
            resp = await client.get(
                f"{settings.auth_service_url}/users/me/risk-profile",
                headers=headers,
            )
            if resp.status_code == 200:
                risk_profile = resp.json()
        except Exception as e:
            logger.warning(f"Risk profile fetch failed: {e}")

        # 2. Get first active portfolio + analysis
        try:
            resp = await client.get(
                f"{settings.portfolio_service_url}/portfolios/",
                headers=headers,
            )
            if resp.status_code == 200 and resp.json():
                portfolio_id = resp.json()[0]["id"]

                analysis_resp = await client.get(
                    f"{settings.portfolio_service_url}/holdings/{portfolio_id}/analysis",
                    headers=headers,
                )
                if analysis_resp.status_code == 200:
                    portfolio_summary = analysis_resp.json()
        except Exception as e:
            logger.warning(f"Portfolio fetch failed: {e}")

        return portfolio_summary, risk_profile