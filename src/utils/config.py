"""Configuration management for Life DB."""

import os
from pathlib import Path
from typing import Any, Dict, List

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class AppConfig(BaseModel):
    """Application configuration."""

    name: str = "Life DB"
    version: str = "0.1.0"
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False


class DatabaseConfig(BaseModel):
    """Database configuration."""

    path: str = "./db/lifedb.sqlite"
    echo: bool = False
    pool_size: int = 5
    max_overflow: int = 10


class IngestionConfig(BaseModel):
    """Document ingestion configuration."""

    watch_directories: List[str] = Field(default_factory=lambda: ["./data"])
    supported_extensions: List[str] = Field(
        default_factory=lambda: [
            ".docx",
            ".xlsx",
            ".pptx",
            ".pdf",
            ".msg",
            ".eml",
            ".txt",
            ".md",
            ".png",
            ".jpg",
            ".jpeg",
        ]
    )
    max_file_size_mb: int = 100
    parallel_workers: int = 4
    ignore_patterns: List[str] = Field(default_factory=lambda: [".*", "~$*", "*.tmp"])


class SearchConfig(BaseModel):
    """Search configuration."""

    results_per_page: int = 50
    max_results: int = 1000
    snippet_length: int = 64
    enable_typo_tolerance: bool = False
    min_query_length: int = 2


class OCRConfig(BaseModel):
    """OCR configuration."""

    enabled: bool = True
    languages: List[str] = Field(default_factory=lambda: ["en"])
    gpu: bool = False
    min_confidence: float = 0.3


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: str = "./logs/lifedb.log"
    max_bytes: int = 10485760  # 10MB
    backup_count: int = 5


class PerformanceConfig(BaseModel):
    """Performance configuration."""

    enable_cache: bool = True
    cache_ttl: int = 300
    batch_size: int = 100
    async_enabled: bool = True


class FileWatcherConfig(BaseModel):
    """File watcher configuration."""

    enabled: bool = True
    debounce_delay: int = 2
    watch_events: List[str] = Field(
        default_factory=lambda: ["created", "modified", "moved"]
    )


class Settings(BaseSettings):
    """Main settings class."""

    app: AppConfig = Field(default_factory=AppConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    ingestion: IngestionConfig = Field(default_factory=IngestionConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    ocr: OCRConfig = Field(default_factory=OCRConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    file_watcher: FileWatcherConfig = Field(default_factory=FileWatcherConfig)

    class Config:
        """Pydantic configuration."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


def load_settings(config_path: str = "config/settings.yaml") -> Settings:
    """Load settings from YAML file.

    Args:
        config_path: Path to configuration file

    Returns:
        Settings object with loaded configuration
    """
    config_file = Path(config_path)

    if not config_file.exists():
        print(f"Config file not found at {config_path}, using defaults")
        return Settings()

    try:
        with open(config_file, "r") as f:
            config_dict = yaml.safe_load(f)

        # Convert nested dicts to proper models
        settings_data = {}
        for key, value in config_dict.items():
            if isinstance(value, dict):
                # Find the appropriate config class
                config_class = {
                    "app": AppConfig,
                    "database": DatabaseConfig,
                    "ingestion": IngestionConfig,
                    "search": SearchConfig,
                    "ocr": OCRConfig,
                    "logging": LoggingConfig,
                    "performance": PerformanceConfig,
                    "file_watcher": FileWatcherConfig,
                }.get(key)

                if config_class:
                    settings_data[key] = config_class(**value)
            else:
                settings_data[key] = value

        return Settings(**settings_data)

    except Exception as e:
        print(f"Error loading config: {e}, using defaults")
        return Settings()


# Global settings instance
settings = load_settings()


def get_settings() -> Settings:
    """Get the global settings instance.

    Returns:
        Settings object
    """
    return settings


if __name__ == "__main__":
    # Test configuration loading
    config = get_settings()
    print(f"App: {config.app.name} v{config.app.version}")
    print(f"Database: {config.database.path}")
    print(f"Watch directories: {config.ingestion.watch_directories}")
    print(f"Supported extensions: {len(config.ingestion.supported_extensions)}")
    print(f"OCR enabled: {config.ocr.enabled}")
