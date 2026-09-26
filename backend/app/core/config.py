import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "DocuMind"
    API_V1_STR: str = "/api"
    SECRET_KEY: str = "documind_super_secret_jwt_key_2026"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    ALGORITHM: str = "HS256"

    # MySQL Database
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "root"
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_DB: str = "documind_db"

    # ChromaDB
    CHROMA_PERSIST_DIRECTORY: str = "./chroma_data"

    # Gemini
    GEMINI_API_KEY: Optional[str] = ""

    # Storage
    UPLOAD_DIR: str = "./uploads"

    # Tesseract
    TESSERACT_CMD: Optional[str] = None

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}?charset=utf8mb4"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
