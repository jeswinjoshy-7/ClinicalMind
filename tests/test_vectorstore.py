"""
Tests for the ClinicalMind vector store components.
"""
import pytest
import os
import shutil
from pathlib import Path

from langchain_core.documents import Document

from src.vectorstore.store_manager import ClinicalStoreManager
from configs.config import settings


class TestClinicalStoreManager:
    """Test suite for ClinicalStoreManager."""

    @pytest.fixture
    def store_manager(self):
        """Create a fresh store manager for testing."""
        manager = ClinicalStoreManager()
        yield manager
        # Cleanup after tests
        for store_name in manager.store_names:
            manager.clear_store(store_name)

    @pytest.fixture
    def sample_documents(self):
        """Create sample documents for testing."""
        return [
            Document(
                page_content="Metformin is the first-line treatment for Type 2 Diabetes.",
                metadata={"filename": "diabetes_guidelines.pdf", "page": 1}
            ),
            Document(
                page_content="The recommended dosage is 500mg twice daily with meals.",
                metadata={"filename": "diabetes_guidelines.pdf", "page": 2}
            ),
        ]

    def test_initialization(self, store_manager):
        """Test that store manager initializes correctly."""
        assert store_manager.store_names == ["guidelines", "drugs", "patients"]
        assert store_manager.embeddings is not None

    def test_add_documents(self, store_manager, sample_documents):
        """Test adding documents to a store."""
        store_manager.add_documents("guidelines", sample_documents)
        
        # Verify store is no longer None
        assert store_manager.stores["guidelines"] is not None
        
        # Verify metadata file was created
        metadata_path = Path(settings.vectorstore.clinical_index_path) / "metadata.json"
        assert metadata_path.exists()

    def test_search_returns_results(self, store_manager, sample_documents):
        """Test that search returns relevant documents."""
        store_manager.add_documents("guidelines", sample_documents)
        
        results = store_manager.search("guidelines", "Metformin dosage")
        
        assert len(results) > 0
        assert "Metformin" in results[0].page_content

    def test_search_with_threshold(self, store_manager, sample_documents):
        """Test search with similarity threshold."""
        store_manager.add_documents("guidelines", sample_documents)
        
        # High threshold should return fewer or no results
        results = store_manager.search(
            "guidelines", 
            "unrelated query about astronomy",
            threshold=0.9
        )
        
        assert len(results) == 0

    def test_invalid_store_name(self, store_manager):
        """Test that invalid store names raise errors."""
        with pytest.raises(ValueError, match="Invalid store name"):
            store_manager.add_documents("invalid_store", [])

    def test_clear_store(self, store_manager, sample_documents):
        """Test clearing a store."""
        store_manager.add_documents("drugs", sample_documents)
        store_manager.clear_store("drugs")
        
        assert store_manager.stores["drugs"] is None

    def test_get_metadata(self, store_manager, sample_documents):
        """Test retrieving metadata for all stores."""
        store_manager.add_documents("patients", sample_documents)
        
        metadata = store_manager.get_all_metadata()
        
        assert "guidelines" in metadata
        assert "drugs" in metadata
        assert "patients" in metadata
        assert metadata["patients"]["status"] != "empty"
