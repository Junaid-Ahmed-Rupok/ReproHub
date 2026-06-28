"""
Application configuration settings.
Loads environment variables and provides configuration for all app components.
"""
import os
import secrets
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


class Config:
    """Application configuration."""

    # App metadata
    APP_NAME = "ReproHub"
    APP_VERSION = "1.0.0"
    APP_DESCRIPTION = "Research Reproducibility Verification Platform"

    # Environment
    ENV = os.getenv("APP_ENV", "development").lower()
    DEBUG = os.getenv("APP_DEBUG", "True").lower() == "true"

    # SECRET_KEY: only auto-generate a throwaway value in development.
    # In production this must come from the environment - no insecure fallback.
    _DEV_SECRET_FALLBACK = "dev-secret-key-change-in-production"
    SECRET_KEY = os.getenv("APP_SECRET_KEY", "")
    if not SECRET_KEY:
        if ENV == "production":
            SECRET_KEY = ""  # left empty deliberately; validate() will raise
        else:
            SECRET_KEY = _DEV_SECRET_FALLBACK

    # File upload settings
    MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "100"))
    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
    ALLOWED_PAPER_EXTENSIONS = [".pdf"]
    ALLOWED_DATA_EXTENSIONS = [".csv", ".xlsx"]

    # AI/LLM settings
    # No hardcoded model default - must be explicit so nobody silently runs
    # against a stale/wrong model. Set AI_MODEL in your .env.
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    AI_MODEL = os.getenv("AI_MODEL", "")
    AI_TEMPERATURE = float(os.getenv("AI_TEMPERATURE", "0.0"))
    AI_MAX_TOKENS = int(os.getenv("AI_MAX_TOKENS", "4000"))

    # Cache settings
    CACHE_ENABLED = os.getenv("CACHE_ENABLED", "True").lower() == "true"
    CACHE_TTL_HOURS = int(os.getenv("CACHE_TTL_HOURS", "24"))

    # Paths
    BASE_DIR = Path(__file__).resolve().parent.parent
    DATA_DIR = BASE_DIR / "data"
    RAW_DATA_DIR = DATA_DIR / "raw"
    PROCESSED_DATA_DIR = DATA_DIR / "processed"
    BENCHMARK_DIR = DATA_DIR / "benchmarks"
    STATIC_DIR = BASE_DIR / "static"
    TEMPLATE_DIR = STATIC_DIR / "templates"

    @classmethod
    def ensure_directories(cls) -> None:
        """Create all required directories if they don't exist."""
        dirs = [
            cls.RAW_DATA_DIR,
            cls.PROCESSED_DATA_DIR,
            cls.BENCHMARK_DIR,
            cls.TEMPLATE_DIR,
        ]
        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)

    @classmethod
    def validate(cls, require_ai: bool = True) -> None:
        """
        Validate that required configuration is present for the current
        environment. Call this once at startup. Fails loudly instead of
        letting bad config surface later as a confusing runtime error.

        Args:
            require_ai: if True, require OPENAI_API_KEY and AI_MODEL to be
                set. Set False only for contexts that never call the LLM
                (e.g. running the statistical engine's unit tests in
                isolation).
        """
        errors = []

        if cls.ENV == "production":
            if not cls.SECRET_KEY or cls.SECRET_KEY == cls._DEV_SECRET_FALLBACK:
                errors.append(
                    "APP_SECRET_KEY must be set to a real secret in production "
                    "(no insecure default is allowed)."
                )
            if cls.DEBUG:
                errors.append(
                    "APP_DEBUG must be False in production."
                )

        if require_ai:
            if not cls.OPENAI_API_KEY:
                errors.append("OPENAI_API_KEY is not set.")
            if not cls.AI_MODEL:
                errors.append(
                    "AI_MODEL is not set. Pick a current model explicitly in "
                    ".env - there is no default, to avoid silently running "
                    "against a stale model."
                )

        if cls.MAX_FILE_SIZE_MB <= 0:
            errors.append("MAX_FILE_SIZE_MB must be a positive integer.")

        if errors:
            raise ConfigError(
                "Invalid configuration:\n  - " + "\n  - ".join(errors)
            )

    @classmethod
    def is_allowed_paper(cls, filename: str) -> bool:
        """Check if file is an allowed paper format."""
        ext = Path(filename).suffix.lower()
        return ext in cls.ALLOWED_PAPER_EXTENSIONS

    @classmethod
    def is_allowed_data(cls, filename: str) -> bool:
        """Check if file is an allowed data format."""
        ext = Path(filename).suffix.lower()
        return ext in cls.ALLOWED_DATA_EXTENSIONS

    @classmethod
    def get_max_file_size_mb(cls) -> int:
        """Get max file size in MB."""
        return cls.MAX_FILE_SIZE_MB

    @classmethod
    def check_file_size(cls, size_bytes: int) -> bool:
        """Check whether a given file size in bytes is within the allowed limit."""
        return 0 <= size_bytes <= cls.MAX_FILE_SIZE_BYTES


# Singleton instance
config = Config()
