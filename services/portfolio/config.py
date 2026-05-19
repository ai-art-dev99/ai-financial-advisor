from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://robo_user:password@postgres:5432/robo_portfolio"
    timescale_url: str = "postgresql+asyncpg://robo_user:password@timescale:5432/robo_market"
    redis_url: str = "redis://redis:6379/1"
    auth_service_url: str = "http://auth:8000"
    cors_origins: str = "http://localhost:3000,http://localhost,http://localhost:8080"

    def get_cors_origins(self) -> list[str]:
        origins = [o.strip() for o in self.cors_origins.split(",")]
        production_origins = [
            "https://argo-advisor.com",
            "https://www.argo-advisor.com",
            "https://api.argo-advisor.com",
        ]
        return list(set(origins + production_origins))

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()