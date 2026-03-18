from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # FalkorDB — set FALKORDB_EMBEDDED=true for local/test use (no server required)
    falkordb_embedded: bool = False
    falkordb_host: str = "localhost"
    falkordb_port: int = 6379
    falkordb_graph: str = "entmoot"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 7000
    debug: bool = False

    # Admin
    admin_api_key: str = "changeme-admin"


settings = Settings()
