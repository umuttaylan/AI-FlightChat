import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    ANTHROPIC_API_KEY: str | None = os.getenv("ANTHROPIC_API_KEY")
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307")

    AMADEUS_API_KEY = os.getenv("AMADEUS_API_KEY")
    AMADEUS_API_SECRET = os.getenv("AMADEUS_API_SECRET")
    AMADEUS_ENV = os.getenv("AMADEUS_ENV", "test")

    GRADIO_SHARE: bool = os.getenv("GRADIO_SHARE", "false").lower() == "true"

    IMAGE_MODEL: str = os.getenv("IMAGE_MODEL", "dall-e-3")

settings = Settings()
