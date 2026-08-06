from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # app
    LLM_API_URL: str
    LLM_API_KEY: str
    LLM_MODEL: str
    SLM_API_URL: str
    SLM_API_KEY: str
    SLM_MODEL: str
    EMBEDDING_API_URL: str
    EMBEDDING_API_KEY: str
    EMBEDDING_MODEL: str
    PG_HOST: str
    PG_PORT: int
    PG_USER: str
    PG_USER_PASSWD: str
    PG_DATABASE: str
    DATA_PATH: str
    DEBUG:str
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
