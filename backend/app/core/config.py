from pydantic import BaseModel, Field
from typing import List
import os

# Database configuration overrides - Force .env values
from dotenv import load_dotenv
import pathlib

# Path to .env
load_dotenv()

# Load into a dict
# config = dotenv_values(env_path)
class Settings(BaseModel):
    # API Configuration
    api_title: str = "AI Tutor SaaS Platform API"
    api_version: str = "1.0.0"
    api_description: str = "AI-powered tutoring platform integrated with Canvas LMS"
    
    CANVAS_URL: str = os.getenv("CANVAS_URL")
    CANVAS_API_TOKEN: str = os.getenv("CANVAS_API_TOKEN")

    # LTI Configuratio
    LTI_CONSUMER_KEY: str = os.getenv("LTI_CONSUMER_KEY")
    LTI_SHARED_SECRET: str = os.getenv("LTI_SHARED_SECRET")
    
    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    environment: str = "development"
    
    # AI Configuration (required by services)
    google_api_key: str = Field(default="", description="Google Cloud API Key")
    gemini_model: str = Field(default="gemini-2.5-pro", description="Gemini model to use")
    
    # Memory Configuration (required by memory service)
    memory_file_path: str = Field(default="data/conversation_memory", description="Path to store conversation memory")
    memory_window_size: int = Field(default=20, description="Number of conversation exchanges to keep in memory")
    memory_persistence: bool = Field(default=True, description="Whether to persist conversation memory")
    
    # CORS Configuration (required by main.py)
    allowed_origins: List[str] = Field(
        default=[os.getenv("AI_TUTOR_ALLOWED_ORIGINS", "*")],
        description="Allowed CORS origins"
    )
    
    # Database Configuration
    db_host: str = Field(default=os.getenv("DB_HOST"), description="PostgreSQL host")
    db_port: int = Field(default=5432, description="PostgreSQL port")
    db_name: str = Field(default=os.getenv("DB_NAME"), description="PostgreSQL database name")
    db_user: str = Field(default=os.getenv("DB_USER"), description="PostgreSQL username")
    db_password: str = Field(default=os.getenv("DB_PASSWORD"), description="PostgreSQL password")
    
    # Logging Configuration
    log_level: str = Field(default="INFO", description="Logging level")

    @property
    def connection_url(self) -> str:
        """Construct PostgreSQL connection URL from environment variables"""
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}?ssl=require"

# Create settings instance
settings = Settings()

# Set Google credentials for Vertex AI
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(pathlib.Path(__file__).resolve().parent.parent.parent / "elivision-ai-1-4e63af45bd31.json")

# Log the actual values being used
print(f"Database configuration: {settings.db_host}:{settings.db_port}/{settings.db_name} (user: {settings.db_user})")
print(f"Google credentials: {os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')}")

if os.getenv("LOG_LEVEL"):
    settings.log_level = os.getenv("LOG_LEVEL")