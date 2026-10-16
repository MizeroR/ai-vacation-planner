from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    anthropic_api_key: str
    anthropic_model: str = "claude-3-5-haiku-latest"
    anthropic_max_tokens: int = 1200
    anthropic_temperature: float = 0.0
    agent_max_steps: int = 4
    external_request_timeout_seconds: int = 10
    stt_model: str = "small"
    tts_engine: str = "pyttsx3"
    tts_voice: str | None = None
    max_audio_upload_bytes: int = 25_000_000
    max_image_upload_bytes: int = 10_000_000
    mcp_server_url: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
