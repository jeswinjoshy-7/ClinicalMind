import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

from configs.config import settings
from src.vectorstore.store_manager import ClinicalStoreManager
from src.graph.clinical_graph import MultiAgentClinicalGraph, ClinicalResponse
from src.utils.safety import MedicalSafetyChecker, SafetyResult
from src.document.processor import DocumentProcessor, ProcessedDocument

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ClinicalQueryResult:
    """Structured result for clinical queries."""
    query: str
    answer: str
    sources: List[str]
    risk_level: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class ClinicalSupervisor:
    """
    The main orchestrator for ClinicalMind.
    
    Coordinates document processing, vector storage, multi-agent 
    reasoning via LangGraph, and safety enforcement.
    """

    def __init__(self):
        """Initialize all core components and conversation memory."""
        logger.info("Initializing ClinicalSupervisor...")
        
        # Core Components
        self.store_manager = ClinicalStoreManager()
        self.graph = MultiAgentClinicalGraph(self.store_manager)
        self.safety_checker = MedicalSafetyChecker()
        self.processor = DocumentProcessor()
        
        # Memory Management
        self.history: List[BaseMessage] = []
        self.max_history_len: int = 10  # Number of message exchanges to keep

    def ingest_document(self, file_path: str, store_name: str) -> Dict[str, Any]:
        """
        Processes and indexes a document into the specified store.
        
        Args:
            file_path: Path to the document (PDF, DOCX, TXT).
            store_name: Target store ('guidelines', 'drugs', 'patients').
            
        Returns:
            Status dictionary with processing details.
        """
        try:
            processed_doc: ProcessedDocument = self.processor.process_file(file_path)
            self.store_manager.add_documents(store_name, processed_doc.chunks)
            
            logger.info(f"Successfully ingested {file_path} into {store_name}")
            return {
                "status": "success",
                "filename": processed_doc.source_path,
                "chunks_added": processed_doc.total_chunks,
                "timestamp": processed_doc.processed_at
            }
        except Exception as e:
            logger.error(f"Ingestion failed for {file_path}: {e}")
            return {"status": "error", "message": str(e)}

    def query(self, user_query: str) -> ClinicalQueryResult:
        """
        Executes a multi-agent clinical query with memory window handling.
        
        Args:
            user_query: The clinical question.
            
        Returns:
            ClinicalQueryResult with answer, sources, and safety assessment.
        """
        # 1. Pre-check: Safety validation of the query itself
        query_safety: SafetyResult = self.safety_checker.check_content(user_query)
        
        # 2. Add query to history
        self.history.append(HumanMessage(content=user_query))
        self._trim_history()

        # 3. Invoke LangGraph workflow
        # Note: In a multi-turn graph, we'd pass the full history. 
        # Here we use the graph's internal invoke which handles the reasoning.
        response: ClinicalResponse = self.graph.invoke(user_query)
        
        # 4. Post-check: Append safety disclaimers to the final answer
        final_answer = self.safety_checker.append_disclaimer(response.answer, query_safety)
        
        # 5. Save response to history
        self.history.append(AIMessage(content=response.answer))
        
        return ClinicalQueryResult(
            query=user_query,
            answer=final_answer,
            sources=response.sources,
            risk_level=query_safety.risk_level.value
        )

    def _trim_history(self) -> None:
        """Maintains the conversation window size to prevent context overflow."""
        if len(self.history) > (self.max_history_len * 2):
            # Keep the most recent N exchanges (Human + AI pairs)
            self.history = self.history[-(self.max_history_len * 2):]
            logger.debug(f"Trimmed history to {len(self.history)} messages.")

    def clear_store(self, store_name: str) -> None:
        """Clears a specific vector store."""
        self.store_manager.clear_store(store_name)
        logger.info(f"Cleared store: {store_name}")

    def clear_all(self) -> None:
        """Wipes all clinical databases and memory."""
        for store in ["guidelines", "drugs", "patients"]:
            self.store_manager.clear_store(store)
        self.history = []
        logger.info("Cleared all stores and conversation history.")

    def get_system_status(self) -> Dict[str, Any]:
        """Returns the current operational status and database metrics."""
        return {
            "database": self.store_manager.get_all_metadata(),
            "memory_depth": len(self.history) // 2,
            "safety_filter_enabled": settings.safety.enable_safety_filter,
            "llm_model": settings.llm.model_name
        }
