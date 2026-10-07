from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = Field(default="sqlite:///./upay_demo.sqlite3", alias="DATABASE_URL")
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    groq_model: str = Field(default="qwen/qwen3.8-27b", alias="GROQ_MODEL")
    ai_enabled: bool = Field(default=True, alias="AI_ENABLED")
    groq_timeout_seconds: float = Field(default=10, ge=1, le=60, alias="GROQ_TIMEOUT_SECONDS")
    jwt_secret_key: str = Field(default="demo-only-change-me", alias="JWT_SECRET_KEY")
    frontend_url: str = Field(default="http://localhost:5173", alias="FRONTEND_URL")
    environment: str = Field(default="development", alias="ENVIRONMENT")

@lru_cache
def get_settings() -> Settings: return Settings()
