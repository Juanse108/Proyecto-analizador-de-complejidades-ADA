from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    APP_NAME: str = "llm_service"
    ENV: str = "dev"

    # Gemini
    GEMINI_MODEL: str = "gemini-1.5-flash"
    GEMINI_API_KEY: str | None = None
    GEMINI_TIMEOUT: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",  # usa variables tal cual
        extra="ignore"  # ignora variables desconocidas
    )


settings = Settings()
