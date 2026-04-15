from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path


class Settings(BaseSettings):
    # Ollama
    model_name: str = Field(default="gpt-oss:120b-cloud", env="MODEL_NAME")
    ollama_base_url: str = Field(default="http://localhost:11434", env="OLLAMA_BASE_URL")
    temperature: float = Field(default=0.3, env="TEMPERATURE")

    # Server — use port 8001 to avoid conflict with the main A2A backend on 8000
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8001, env="PORT")

    # Paths
    upload_dir: str = Field(default="./uploads", env="UPLOAD_DIR")
    output_dir: str = Field(default="./outputs", env="OUTPUT_DIR")
    vectorstore_dir: str = Field(default="./vectorstore", env="VECTORSTORE_DIR")

    # RAG
    chunk_size: int = Field(default=1500, env="CHUNK_SIZE")
    chunk_overlap: int = Field(default=200, env="CHUNK_OVERLAP")
    top_k_results: int = Field(default=8, env="TOP_K_RESULTS")
    rag_distance_threshold: float = Field(default=0.45, env="RAG_DISTANCE_THRESHOLD")
    rag_min_token_overlap: int = Field(default=2, env="RAG_MIN_TOKEN_OVERLAP")

    # Document
    default_font: str = Field(default="Calibri", env="DEFAULT_FONT")
    default_font_size: int = Field(default=11, env="DEFAULT_FONT_SIZE")

    # Content generation model (can differ from planning model for quality/speed split)
    content_model_name: str = Field(default="", env="CONTENT_MODEL_NAME")

    # Named RAG collections
    upi_knowledge_collection: str = Field(default="upi_knowledge", env="UPI_KNOWLEDGE_COLLECTION")
    upi_code_collection: str = Field(default="upi_code", env="UPI_CODE_COLLECTION")

    # Parallel section generation (number of concurrent LLM calls for write_content)
    max_parallel_sections: int = Field(default=3, env="MAX_PARALLEL_SECTIONS")

    # LLM provider: "ollama" for local Ollama, "openai_compat" for vLLM/LiteLLM OpenAI-compatible endpoints
    llm_provider: str = Field(default="ollama", env="LLM_PROVIDER")
    # For openai_compat provider: base URL of the OpenAI-compatible endpoint
    openai_base_url: str = Field(default="http://183.82.7.228:9535/v1", env="OPENAI_BASE_URL")
    # API key for openai_compat provider (use "none" or "EMPTY" for local vLLM endpoints that don't require auth)
    openai_api_key: str = Field(default="none", env="OPENAI_API_KEY")
    # Model name for openai_compat provider (e.g. "/model" for vLLM)
    openai_model_name: str = Field(default="/model", env="OPENAI_MODEL_NAME")

    class Config:
        env_file = (
            str(Path(__file__).resolve().parents[1] / ".env"),
            ".env",
        )
        env_file_encoding = "utf-8"
        extra = "ignore"

    def ensure_dirs(self):
        Path(self.upload_dir).mkdir(parents=True, exist_ok=True)
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        Path(self.vectorstore_dir).mkdir(parents=True, exist_ok=True)

    @property
    def effective_content_model(self) -> str:
        """Content model falls back to planning model if not separately configured."""
        return self.content_model_name.strip() or self.model_name


settings = Settings()
settings.ensure_dirs()
