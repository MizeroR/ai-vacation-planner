from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    anthropic_api_key: str
    anthropic_model: str = "claude-3-5-haiku-latest"
    anthropic_max_tokens: int = 1200
    anthropic_temperature: float = 0.0

    class Config:
        env_file = ".env"


settings = Settings()
