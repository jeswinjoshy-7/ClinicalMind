import os
import json
import logging
import shutil
from typing import List, Dict, Optional, Any, Union
from pathlib import Path

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from configs.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ClinicalStoreManager:
    """
    Manages multiple FAISS vector stores for clinical intelligence.
    
    Handles initialization, persistence, document ingestion, and 
    threshold-based retrieval for Guidelines, Drugs, and Patient indices.
    """

    def __init__(self):
        """Initialize embeddings and store containers."""
        self.embeddings = HuggingFaceEmbeddings(
            model_name=settings.embedding.model_name,
            model_kwargs={'device': settings.embedding.device}
        )
        
        # Define store names as per requirements
        self.store_names = ["guidelines", "drugs", "patients"]
        self.stores: Dict[str, Optional[FAISS]] = {name: None for name in self.store_names}
        
        # Map store names to paths (derived from settings or defaults)
        self.paths: Dict[str, Path] = {
            "guidelines": Path(settings.vectorstore.clinical_index_path),
            "drugs": Path(settings.vectorstore.research_index_path),
            "patients": Path(settings.vectorstore.general_index_path)
        }
        
        # Ensure data directories exist
        for path in self.paths.values():
            path.parent.mkdir(parents=True, exist_ok=True)

        self._load_all_stores()

    def _load_all_stores(self) -> None:
        """Load existing FAISS indices from disk or initialize empty ones."""
        for name in self.store_names:
            path = self.paths[name]
            if (path / "index.faiss").exists():
                try:
                    self.stores[name] = FAISS.load_local(
                        str(path), 
                        self.embeddings, 
                        allow_dangerous_deserialization=True
                    )
                    logger.info(f"Loaded existing store: {name}")
                except Exception as e:
                    logger.error(f"Failed to load store {name}: {e}")
                    self.stores[name] = None
            else:
                logger.info(f"Store {name} not found at {path}. Initializing empty.")
                self.stores[name] = None

    def add_documents(self, store_name: str, documents: List[Document]) -> None:
        """
        Add documents to a specific vector store.
        
        Args:
            store_name: The target store ('guidelines', 'drugs', 'patients').
            documents: List of LangChain Document objects.
        """
        if store_name not in self.store_names:
            raise ValueError(f"Invalid store name: {store_name}. Choose from {self.store_names}")

        if self.stores[store_name] is None:
            self.stores[store_name] = FAISS.from_documents(documents, self.embeddings)
        else:
            self.stores[store_name].add_documents(documents)
        
        self.save_store(store_name)
        self._update_metadata_json(store_name)

    def search(
        self,
        store_name: str,
        query: str,
        top_k: Optional[int] = None,
        threshold: Optional[float] = None
    ) -> List[Document]:
        """
        Perform similarity search with optional threshold filtering.

        Args:
            store_name: The store to search in.
            query: The search string.
            top_k: Number of documents to return.
            threshold: Minimum similarity score (0.0 to 1.0).

        Returns:
            List of filtered Document objects.
        """
        if self.stores[store_name] is None:
            logger.warning(f"Search attempted on empty store: {store_name}")
            return []

        k = top_k or settings.retrieval.top_k
        min_score = threshold or settings.retrieval.score_threshold

        # similarity_search_with_relevance_scores returns (doc, score)
        # For cosine similarity (default with MiniLM), score ranges from -1 to 1
        # where 1 is most similar. We filter to keep only results >= threshold.
        results_with_score = self.stores[store_name].similarity_search_with_relevance_scores(query, k=k)

        filtered_docs = [
            doc for doc, score in results_with_score
            if score >= min_score
        ]

        return filtered_docs

    def save_store(self, store_name: str) -> None:
        """Persist a FAISS index to disk."""
        if self.stores[store_name]:
            self.stores[store_name].save_local(str(self.paths[store_name]))
            logger.info(f"Saved store {store_name} to {self.paths[store_name]}")

    def clear_store(self, store_name: str) -> None:
        """Remove a store from memory and disk."""
        if store_name not in self.store_names:
            raise ValueError(f"Invalid store name: {store_name}")

        self.stores[store_name] = None
        if self.paths[store_name].exists():
            shutil.rmtree(self.paths[store_name])
            logger.info(f"Cleared store and deleted files for: {store_name}")

    def _update_metadata_json(self, store_name: str) -> None:
        """
        Saves custom metadata JSON for the store, including document count.
        """
        if self.stores[store_name] is None:
            return

        metadata = {
            "store_name": store_name,
            "document_count": len(self.stores[store_name].docstore._dict),
            "embedding_model": settings.embedding.model_name,
            "last_updated": str(Path(self.paths[store_name]).stat().st_mtime if self.paths[store_name].exists() else "N/A")
        }
        
        meta_path = self.paths[store_name] / "metadata.json"
        with open(meta_path, 'w') as f:
            json.dump(metadata, f, indent=4)
        logger.info(f"Updated metadata JSON for {store_name}")

    def get_all_metadata(self) -> Dict[str, Any]:
        """Returns metadata for all stores."""
        all_meta = {}
        for name in self.store_names:
            meta_path = self.paths[name] / "metadata.json"
            if meta_path.exists():
                with open(meta_path, 'r') as f:
                    all_meta[name] = json.load(f)
            else:
                all_meta[name] = {"status": "empty"}
        return all_meta
