from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    anthropic_api_key: str
    anthropic_model: str = "claude-haiku-5-5"
    anthropic_max_tokens: int = 1200
    agent_max_steps: int = 4
    external_request_timeout_seconds: int = 10
    stt_model: str = "small"
    tts_engine: str = "pyttsx3"
    tts_voice: str | None = None
    max_audio_upload_bytes: int = 25_000_000
    max_image_upload_bytes: int = 10_000_000
    mcp_server_url: str | None = None
    datadog_enabled: bool = False
    datadog_service: str = "ai-vacation-planner"
    datadog_env: str = "development"
    datadog_agent_host: str = Field(
        default="localhost",
        validation_alias=AliasChoices("DD_AGENT_HOST", "DATADOG_AGENT_HOST"),
    )
    datadog_trace_agent_port: int = Field(
        default=8126,
        validation_alias=AliasChoices(
            "DD_TRACE_AGENT_PORT",
            "DATADOG_TRACE_AGENT_PORT",
        ),
    )
    datadog_statsd_port: int = Field(
        default=8125,
        validation_alias=AliasChoices(
            "DD_DOGSTATSD_PORT",
            "DATADOG_STATSD_PORT",
        ),
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
