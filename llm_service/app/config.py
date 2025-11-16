"""
Módulo de configuración para el microservicio de LLM (Gemini).

Utiliza `pydantic-settings` para cargar la configuración desde variables
de entorno y/o archivos `.env`. Todos los atributos definidos en `Settings`
pueden sobreescribirse mediante variables de entorno con el mismo nombre.

Ejemplo de `.env`:
    APP_NAME=llm_service
    ENV=prod
    GEMINI_MODEL=gemini-2.0-flash
    GEMINI_API_KEY=tu_api_key
    GEMINI_TIMEOUT=60
    LLM_RETRY_MAX=4
    LLM_RETRY_BASE=0.7
    LLM_FALLBACK_MODELS=gemini-2.0-pro
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuración central del microservicio LLM.

    Todos los campos aquí definidos se leen desde variables de entorno
    (y opcionalmente desde un archivo `.env`) gracias a `pydantic-settings`.

    Atributos principales:
        APP_NAME:
            Nombre de la aplicación (aparece en la documentación de FastAPI).
        ENV:
            Entorno de ejecución: "dev", "prod", "test", etc.
        GEMINI_MODEL:
            Modelo principal de la familia Gemini 2.0 a utilizar.
        GEMINI_API_KEY:
            API key para autenticar contra la API de Google Gemini.
        GEMINI_TIMEOUT:
            Timeout (en segundos) para las llamadas al modelo.
        LLM_RETRY_MAX:
            Número máximo de reintentos ante errores reintentables.
        LLM_RETRY_BASE:
            Base del backoff exponencial entre reintentos.
        LLM_FALLBACK_MODELS:
            Cadena con modelos de fallback separados por coma,
            todos de la familia `gemini-2.0-*`.
    """

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


# Instancia única de configuración usada en el resto de la app
settings = Settings()
