from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5"

    redis_url: str = "redis://redis:6379/5"
    chroma_host: str = "chromadb"
    chroma_port: int = 8000

    portfolio_service_url: str = "http://portfolio:8001"
    auth_service_url: str = "http://auth:8000"

    rag_top_k: int = 5
    rag_chunk_size: int = 800
    rag_chunk_overlap: int = 100

    max_history_messages: int = 20
    session_ttl_seconds: int = 3600

    cors_origins: str = "http://localhost:3000,http://localhost:8080"

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