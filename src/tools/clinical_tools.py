import json
import logging
from typing import List, Dict, Any, Optional
from langchain.tools import tool
from langchain_core.documents import Document

from src.vectorstore.store_manager import ClinicalStoreManager
from src.utils.safety import MedicalSafetyChecker, SafetyResult
from configs.config import settings

# Configure logging
logger = logging.getLogger(__name__)


def format_search_results(docs: List[Document]) -> str:
    """Helper to format search results for agent consumption."""
    if not docs:
        return "No relevant information found in the knowledge base."
    
    formatted = []
    for i, doc in enumerate(docs):
        source = doc.metadata.get("filename", "Unknown Source")
        page = doc.metadata.get("page", "N/A")
        # Extract confidence if available (similarity_search_with_relevance_scores adds this)
        # Note: ClinicalStoreManager returns Documents directly, so we rely on metadata 
        # or assume they passed the threshold.
        
        formatted.append(
            f"Result {i+1}:\n"
            f"Source: {source} (Page: {page})\n"
            f"Content: {doc.page_content}\n"
            "---"
        )
    return "\n".join(formatted)


def create_clinical_tools(store_manager: ClinicalStoreManager):
    """
    Factory function to create the suite of clinical tools.
    
    Args:
        store_manager: Initialized ClinicalStoreManager instance.
        
    Returns:
        List of LangChain tools.
    """
    safety_checker = MedicalSafetyChecker()

    @tool
    def search_clinical_guidelines(query: str) -> str:
        """
        Searches the Clinical Guidelines database for medical protocols, 
        standard procedures, and treatment guidelines.
        Use this for general medical knowledge and 'how-to' clinical questions.
        """
        results = store_manager.search("guidelines", query)
        return format_search_results(results)

    @tool
    def search_drug_database(query: str) -> str:
        """
        Searches the Drug Information database for dosage, indications, 
        contraindications, and side effects of medications.
        Use this for any pharmacology-related queries.
        """
        results = store_manager.search("drugs", query)
        return format_search_results(results)

    @tool
    def search_patient_records(query: str) -> str:
        """
        Searches anonymized Patient Records for history, symptoms, 
        and previous treatment outcomes. 
        Use this to find similar clinical cases or patient-specific history.
        """
        results = store_manager.search("patients", query)
        return format_search_results(results)

    @tool
    def get_knowledge_base_status() -> str:
        """
        Returns the current status of the knowledge base, including 
        document counts and update timestamps for all clinical stores.
        """
        metadata = store_manager.get_all_metadata()
        return json.dumps(metadata, indent=2)

    @tool
    def cross_reference_all(query: str) -> str:
        """
        Performs a comprehensive search across all clinical databases 
        (guidelines, drugs, and patients) and aggregates the findings.
        Use this for complex clinical reasoning that requires multiple perspectives.
        """
        summary = []
        for store in ["guidelines", "drugs", "patients"]:
            results = store_manager.search(store, query, top_k=2)
            if results:
                summary.append(f"### Results from {store.upper()} Store ###")
                summary.append(format_search_results(results))
                summary.append("\n")
        
        return "\n".join(summary) if summary else "No information found across any clinical databases."

    @tool
    def flag_safety_concern(text: str) -> str:
        """
        Analyzes clinical text for high-risk scenarios, prohibited keywords, 
        or safety violations. 
        Returns the risk level and the appropriate medical disclaimer.
        Use this to validate any recommendation before finalizing it.
        """
        result: SafetyResult = safety_checker.check_content(text)
        status = {
            "risk_level": result.risk_level.value,
            "is_safe": result.is_safe,
            "detected_keywords": result.detected_keywords,
            "suggested_disclaimer": result.disclaimer
        }
        return json.dumps(status, indent=2)

    return [
        search_clinical_guidelines,
        search_drug_database,
        search_patient_records,
        get_knowledge_base_status,
        cross_reference_all,
        flag_safety_concern
    ]
