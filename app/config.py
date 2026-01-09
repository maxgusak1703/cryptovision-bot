from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    ENCRYPTION_KEY: str
    TELEGRAM_BOT_TOKEN: str
    GEMINI_API_KEY: str
    
    AI_MODEL_NAME: str = "gemini-1.5-flash"
    
    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()