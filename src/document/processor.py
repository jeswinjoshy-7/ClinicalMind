import os
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    Docx2txtLoader
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from configs.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ProcessedDocument:
    """
    Data structure representing the result of document processing.
    
    Contains the split chunks ready for embedding and overall metadata.
    """
    source_path: str
    document_type: str
    chunks: List[Document]
    total_chunks: int
    processed_at: str = field(default_factory=lambda: datetime.now().isoformat())


class DocumentProcessor:
    """
    Handles loading, cleaning, and chunking of clinical documents.
    
    Supports PDF, DOCX, and TXT formats with automatic metadata enrichment
    for clinical traceability and search optimization.
    """

    def __init__(self):
        """Initialize the text splitter with parameters from settings."""
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk.chunk_size,
            chunk_overlap=settings.chunk.chunk_overlap,
            length_function=len,
            is_separator_regex=False,
        )

    def process_file(self, file_path: str) -> ProcessedDocument:
        """
        Loads a file, splits it into chunks, and enriches with metadata.
        
        Args:
            file_path: Path to the document to process.
            
        Returns:
            A ProcessedDocument object.
            
        Raises:
            ValueError: If the file format is unsupported.
            FileNotFoundError: If the file does not exist.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = path.suffix.lower()
        logger.info(f"Processing document: {path.name} (Type: {ext})")

        # 1. Load the raw document
        raw_docs = self._load_document(str(path), ext)
        
        # 2. Split into chunks
        chunks = self.splitter.split_documents(raw_docs)
        
        # 3. Enrich metadata
        enriched_chunks = self._enrich_metadata(chunks, path, ext)
        
        return ProcessedDocument(
            source_path=str(path),
            document_type=ext.replace(".", ""),
            chunks=enriched_chunks,
            total_chunks=len(enriched_chunks)
        )

    def _load_document(self, file_path: str, extension: str) -> List[Document]:
        """Loads the document based on its extension."""
        try:
            if extension == ".pdf":
                loader = PyPDFLoader(file_path)
            elif extension == ".docx":
                loader = Docx2txtLoader(file_path)
            elif extension in [".txt", ".md"]:
                loader = TextLoader(file_path, encoding="utf-8")
            else:
                raise ValueError(f"Unsupported file format: {extension}")
            
            return loader.load()
        except Exception as e:
            logger.error(f"Error loading {file_path}: {str(e)}")
            raise

    def _enrich_metadata(
        self, 
        chunks: List[Document], 
        path: Path, 
        extension: str
    ) -> List[Document]:
        """
        Adds required metadata to each chunk:
        filename, page, chunk_id, document_type, timestamp
        """
        timestamp = datetime.now().isoformat()
        doc_type = extension.replace(".", "")
        filename = path.name

        for i, chunk in enumerate(chunks):
            # Extract page number if available (from PyPDFLoader)
            page_num = chunk.metadata.get("page", 0)
            
            # Update metadata with requested fields
            chunk.metadata.update({
                "filename": filename,
                "page": page_num,
                "chunk_id": f"{filename}_{i}",
                "document_type": doc_type,
                "timestamp": timestamp,
                "processed_by": "ClinicalMind_Processor"
            })
            
        return chunks

    def process_directory(self, dir_path: str) -> List[ProcessedDocument]:
        """
        Processes all supported documents in a directory.
        
        Args:
            dir_path: Path to the directory containing documents.
            
        Returns:
            A list of ProcessedDocument objects.
        """
        processed_results = []
        path = Path(dir_path)
        
        if not path.is_dir():
            logger.error(f"Provided path is not a directory: {dir_path}")
            return []

        supported_extensions = {".pdf", ".docx", ".txt", ".md"}
        
        for item in path.iterdir():
            if item.is_file() and item.suffix.lower() in supported_extensions:
                try:
                    result = self.process_file(str(item))
                    processed_results.append(result)
                except Exception as e:
                    logger.warning(f"Skipping file {item.name} due to error: {e}")
                    
        return processed_results
