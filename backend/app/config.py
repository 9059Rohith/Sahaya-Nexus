from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./sahaya.db"
    secret_key: str = "local-development-only-change-before-deployment"
    cors_origin: str = "http://localhost:3000"
    app_mode: str = "development"
    data_dir: str = "./data"
    ollama_url: str | None = None
    ollama_model: str = "gemma3:4b"
    speech_model: str = "tiny"
    redis_url: str | None = None
    bff_shared_secret: str | None = None

    @model_validator(mode="after")
    def validate_production(self):
        if self.app_mode == "production":
            if len(self.secret_key) < 32 or self.secret_key.startswith("replace-with") or self.secret_key == "local-development-only-change-before-deployment":
                raise ValueError("Production SECRET_KEY must be a unique value of at least 32 characters")
            if self.database_url.startswith("sqlite"):
                raise ValueError("Production requires PostgreSQL, not SQLite")
        if self.bff_shared_secret is not None and (len(self.bff_shared_secret) < 32 or self.bff_shared_secret.startswith("replace-with")):
            raise ValueError("BFF_SHARED_SECRET must be at least 32 characters")
        if self.bff_shared_secret is not None and self.bff_shared_secret == self.secret_key:
            raise ValueError("BFF_SHARED_SECRET must differ from SECRET_KEY")
        return self


settings = Settings()
