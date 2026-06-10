from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "School Affairs API"
    app_host: str = "0.0.0.0"
    app_port: int = 8810
    log_level: str = "INFO"
    secret_key: str = "replace-this-secret-key"
    access_token_expire_minutes: int = 720
    database_url: str = "mysql+pymysql://school_user:school_pass@db:3306/school_db"
    frontend_origin: str = "http://localhost:3810"
    backup_dir: str = "/app/backups"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
