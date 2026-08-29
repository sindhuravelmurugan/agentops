"""
Central configuration for the AgentOps Python service.

All values are read from environment variables so the same code runs
locally, in Docker, and in CI. See .env.example at the repo root.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Groq's free developer tier: no credit card, OpenAI-compatible API.
    # Get a key at console.groq.com/keys
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    # How long a cached intermediate tool result is considered valid.
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "300"))

    SERVICE_HOST: str = os.getenv("SERVICE_HOST", "0.0.0.0")
    SERVICE_PORT: int = int(os.getenv("SERVICE_PORT", "8000"))

    # Max agent tool-calling loop iterations before we force a stop.
    # This is what keeps a runaway agent from looping forever.
    MAX_AGENT_STEPS: int = int(os.getenv("MAX_AGENT_STEPS", "8"))


settings = Settings()
