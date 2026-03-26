from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    """Configuration for the Groq LLM."""
    model_name: str = Field(default="llama-3.3-70b-versatile", description="The Groq model ID to use.")
    temperature: float = Field(default=0.1, description="Sampling temperature for the LLM.")
    max_tokens: int = Field(default=4096, description="Maximum tokens for LLM generation.")
    timeout: int = Field(default=60, description="Timeout in seconds for API calls.")


class EmbeddingSettings(BaseSettings):
    """Configuration for the Embedding model."""
    model_name: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2", 
        description="The HuggingFace embedding model name."
    )
    device: str = Field(default="cpu", description="Device to run embeddings on (cpu/cuda).")


class VectorStoreSettings(BaseSettings):
    """Configuration for FAISS vector stores."""
    clinical_index_path: str = Field(default="data/vectorstore/clinical_index", description="Path to clinical knowledge index.")
    research_index_path: str = Field(default="data/vectorstore/research_index", description="Path to research paper index.")
    general_index_path: str = Field(default="data/vectorstore/general_index", description="Path to general medical index.")


class RetrievalSettings(BaseSettings):
    """Configuration for document retrieval."""
    top_k: int = Field(default=4, description="Number of documents to retrieve.")
    score_threshold: float = Field(default=0.3, description="Minimum similarity score for relevant chunks.")


class ChunkSettings(BaseSettings):
    """Configuration for text splitting."""
    chunk_size: int = Field(default=1000, description="Size of text chunks.")
    chunk_overlap: int = Field(default=200, description="Overlap between consecutive chunks.")


class AgentSettings(BaseSettings):
    """Configuration for LangGraph agents."""
    max_iterations: int = Field(default=10, description="Max iterations for the agent loop.")
    recursion_limit: int = Field(default=50, description="LangGraph recursion limit.")


class SafetySettings(BaseSettings):
    """Configuration for clinical safety and filtering."""
    prohibited_keywords: List[str] = Field(
        default=[
            "illegal substance",
            "unauthorized procedure",
            "confidential patient data",
            "harmful advice",
            "non-clinical recommendation"
        ],
        description="List of keywords to trigger safety filters."
    )
    enable_safety_filter: bool = Field(default=True, description="Whether to enable content filtering.")


class AppSettings(BaseSettings):
    """Configuration for the Gradio interface."""
    host: str = Field(default="0.0.0.0", description="Host to bind the application.")
    port: int = Field(default=7860, description="Port to run the Gradio UI.")
    debug: bool = Field(default=False, description="Enable debug mode.")
    app_name: str = Field(default="ClinicalMind AI", description="Display name of the application.")


class Settings(BaseSettings):
    """Main settings class aggregating all sub-configs."""
    model_config = SettingsConfigDict(
        env_file="configs/.env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True
    )

    # API Keys
    GROQ_API_KEY: Optional[str] = Field(default=None, description="API Key for Groq Cloud.")

    # Sub-configurations
    llm: LLMSettings = LLMSettings()
    embedding: EmbeddingSettings = EmbeddingSettings()
    vectorstore: VectorStoreSettings = VectorStoreSettings()
    retrieval: RetrievalSettings = RetrievalSettings()
    chunk: ChunkSettings = ChunkSettings()
    agent: AgentSettings = AgentSettings()
    safety: SafetySettings = SafetySettings()
    app: AppSettings = AppSettings()


# Export a singleton instance for project-wide use
settings = Settings()
