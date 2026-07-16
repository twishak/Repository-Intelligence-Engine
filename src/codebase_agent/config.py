from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    data_dir: Path = _PROJECT_ROOT / "data"
    repos_dir: Path = _PROJECT_ROOT / "data" / "repos"
    chroma_dir: Path = _PROJECT_ROOT / "data" / "chroma_db"
    graph_dir: Path = _PROJECT_ROOT / "data" / "graph"
    knowledge_dir: Path = _PROJECT_ROOT / "data" / "knowledge"

    # Language scope for v1: Python only.
    allowed_extensions: tuple[str, ...] = (".py",)
    max_file_size_bytes: int = 500_000

    embedding_model_name: str = "jinaai/jina-embeddings-v2-base-code"
    embedding_device: str | None = (
        None  # None = auto-detect (cuda if available, else cpu)
    )
    embedding_batch_size: int = 32

    api_host: str = "127.0.0.1"
    api_port: int = 8000


settings = Settings()
settings.repos_dir.mkdir(parents=True, exist_ok=True)
settings.chroma_dir.mkdir(parents=True, exist_ok=True)
settings.graph_dir.mkdir(parents=True, exist_ok=True)
settings.knowledge_dir.mkdir(parents=True, exist_ok=True)
