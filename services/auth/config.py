from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://robo_user:password@postgres:5432/robo_auth"
    redis_url: str = "redis://redis:6379/0"

    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    cors_origins: str = "http://localhost:3000,http://localhost,http://localhost:8080"
    environment: str = "development"

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