from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "llm_service"
    ENV: str = "dev"

    # Solo familia Gemini 2.0 por defecto
    GEMINI_MODEL: str = "gemini-2.0-flash"
    GEMINI_API_KEY: str | None = None
    GEMINI_TIMEOUT: int = 30

    # Reintentos y fallback
    LLM_RETRY_MAX: int = 4
    LLM_RETRY_BASE: float = 0.7

    # Fallbacks SOLO de la familia 2.0 (por ejemplo flash -> pro)
    LLM_FALLBACK_MODELS: str = "gemini-2.0-pro"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        extra="ignore",
    )


settings = Settings()
