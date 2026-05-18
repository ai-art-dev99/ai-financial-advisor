from celery import Celery
from celery.schedules import crontab
import os

BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/3")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/4")

app = Celery(
    "market_data",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=["tasks"],
)

app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,

    # Periodic tasks (beat schedule)
    beat_schedule={
        # Fetch major indices every 5 min during market hours
        "fetch-major-indices": {
            "task": "tasks.fetch_quotes",
            "schedule": crontab(minute="*/5", hour="14-21"),  # UTC 14-21 = NYSE hours
            "args": (["SPY", "QQQ", "IWM", "DIA", "GLD", "TLT", "VIX"],),
        },
        # Fetch top stocks every 15 min
        "fetch-top-stocks": {
            "task": "tasks.fetch_quotes",
            "schedule": crontab(minute="*/15", hour="14-21"),
            "args": (["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "BRK-B"],),
        },
        # Daily OHLCV bars after market close
        "fetch-daily-bars": {
            "task": "tasks.fetch_daily_bars",
            "schedule": crontab(hour="22", minute="0"),
            "args": (["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META",
                      "SPY", "QQQ", "IWM", "GLD", "TLT"],),
        },
        # Update asset metadata weekly
        "update-asset-info": {
            "task": "tasks.update_asset_info",
            "schedule": crontab(day_of_week="1", hour="6", minute="0"),
            "args": (["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META",
                      "SPY", "QQQ", "IWM", "GLD", "TLT", "COIN", "BTC-USD"],),
        },
    },
)
