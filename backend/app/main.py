import os
import time
import shutil
import logging
import psutil
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Path, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field

# Ensure ClinicalMind is in the path or use absolute imports
from src.agents.supervisor_agent import ClinicalSupervisor, ClinicalQueryResult
from src.cache.cache_layer import get_query_cache
from src.monitoring.metrics import (
    metrics, 
    logger as clinical_logger, 
    MonitoringMiddleware,
    track_operation,
    get_metrics_endpoint
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Pydantic Models ---

class QueryRequest(BaseModel):
    """Request model for clinical queries."""
    query: str = Field(..., example="What are the current guidelines for treating Type 2 Diabetes?")


class QueryResponse(BaseModel):
    """Response model for clinical queries."""
    response: str
    safety_level: str
    sources: List[str]
    query_time: float
    from_cache: bool = False
    cache_level: Optional[str] = None


class StatusResponse(BaseModel):
    """Response model for system status."""
    database: Dict[str, Any]
    memory_depth: int
    safety_filter_enabled: bool
    llm_model: str
    cache_stats: Dict[str, Any] = None
    system_stats: Dict[str, Any] = None


# --- FastAPI Application ---

app = FastAPI(
    title="ClinicalMind AI API",
    description="Production-grade multi-agent clinical intelligence backend.",
    version="2.0.0"
)

# Add monitoring middleware
app.add_middleware(MonitoringMiddleware)

# Initialize the supervisor (Singleton pattern)
supervisor = ClinicalSupervisor()

# Initialize cache
query_cache = get_query_cache()

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add metrics endpoint
app.add_api_route("/metrics", get_metrics_endpoint(), methods=["GET"], tags=["Monitoring"])

# --- Routes ---

@app.post("/query", response_model=QueryResponse)
async def perform_clinical_query(request: QueryRequest, use_cache: bool = True):
    """
    Executes a multi-agent clinical query using the supervisor orchestrator.

    Validates safety, retrieves context from FAISS, and generates an
    evidence-based response via LangGraph.
    
    Args:
        request: Query request with clinical question
        use_cache: Whether to use cached results (default: True)
    """
    start_time = time.time()
    from_cache = False
    cache_level = None
    
    try:
        # Track active processing
        with track_operation("query_processing", {"query_preview": request.query[:50]}):
            # Check cache first
            if use_cache:
                cached = query_cache.get(request.query)
                if cached:
                    from_cache = True
                    cache_level = cached.get("cache_level", "unknown")
                    query_duration = (time.time() - start_time) * 1000
                    
                    # Track metrics
                    metrics.track_query(
                        status="success",
                        safety_level=cached["safety_level"],
                        from_cache=True,
                        latency=query_duration / 1000,
                        response_length=len(cached["response"])
                    )
                    metrics.track_cache_operation("get", cache_level, "hit")
                    
                    clinical_logger.log_query(
                        query=request.query,
                        response=cached["response"],
                        sources=cached["sources"],
                        risk_level=cached["safety_level"],
                        duration_ms=query_duration,
                        from_cache=True
                    )
                    
                    return QueryResponse(
                        response=cached["response"],
                        safety_level=cached["safety_level"],
                        sources=cached["sources"],
                        query_time=round(query_duration, 4),
                        from_cache=True,
                        cache_level=cache_level
                    )
                
                metrics.track_cache_operation("get", "L1", "miss")
            
            # Execute the query through the supervisor
            result: ClinicalQueryResult = supervisor.query(request.query)
            
            end_time = time.time()
            query_duration = round((end_time - start_time) * 1000, 2)
            
            # Cache the result
            if use_cache:
                query_cache.set(
                    query=request.query,
                    response=result.answer,
                    sources=result.sources,
                    safety_level=result.risk_level
                )
                metrics.track_cache_operation("set", "L1", "success")
            
            # Track metrics
            metrics.track_query(
                status="success",
                safety_level=result.risk_level,
                from_cache=False,
                latency=query_duration / 1000,
                response_length=len(result.answer)
            )
            
            # Log query
            clinical_logger.log_query(
                query=request.query,
                response=result.answer,
                sources=result.sources,
                risk_level=result.risk_level,
                duration_ms=query_duration,
                from_cache=False
            )
            
            return QueryResponse(
                response=result.answer,
                safety_level=result.risk_level,
                sources=result.sources,
                query_time=query_duration,
                from_cache=False,
                cache_level=None
            )
            
    except Exception as e:
        query_duration = (time.time() - start_time) * 1000
        
        # Track error
        metrics.track_query(
            status="error",
            safety_level="UNKNOWN",
            from_cache=False,
            latency=query_duration / 1000,
            response_length=0
        )
        metrics.track_error(type(e).__name__, "/query")
        
        clinical_logger.log_error(
            error_type=type(e).__name__,
            message=str(e),
            endpoint="/query",
            query=request.query
        )
        
        logger.error(f"Query processing error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error during clinical reasoning.")


@app.post("/upload/{doc_type}")
async def upload_clinical_document(
    file: UploadFile = File(...),
    doc_type: str = Path(..., description="The store to upload to: 'guidelines', 'drugs', or 'patients'")
):
    """
    Uploads and processes a clinical document (PDF, DOCX, TXT).
    
    The document is chunked, embedded, and added to the specified FAISS index.
    """
    if doc_type not in ["guidelines", "drugs", "patients"]:
        raise HTTPException(status_code=400, detail="Invalid document type. Must be 'guidelines', 'drugs', or 'patients'.")

    # Ensure the upload directory exists
    upload_dir = "data/raw"
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, file.filename)
    
    try:
        # Save uploaded file to disk for processing
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Ingest into the vector store
        ingest_result = supervisor.ingest_document(file_path, doc_type)
        
        if ingest_result["status"] == "error":
            raise HTTPException(status_code=500, detail=ingest_result["message"])
            
        return ingest_result
    except Exception as e:
        logger.error(f"Upload/Ingestion error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")
    finally:
        # Optionally cleanup the raw file or keep for auditing
        pass


@app.get("/health")
async def health_check():
    """
    Health check endpoint for Docker/Kubernetes.
    Returns basic service status.
    """
    return {
        "status": "healthy",
        "service": "ClinicalMind Backend",
        "version": "1.0.0"
    }


@app.get("/ready")
async def readiness_check():
    """
    Readiness check endpoint for Kubernetes.
    Verifies all dependencies are available.
    """
    try:
        # Check if supervisor is initialized
        _ = supervisor.get_system_status()
        return {
            "status": "ready",
            "database": "connected",
            "llm": "available"
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Service not ready")


@app.get("/status", response_model=StatusResponse)
async def get_system_status():
    """
    Returns the current operational status of the ClinicalMind system,
    including database metrics, cache stats, and system health.
    """
    try:
        status = supervisor.get_system_status()
        
        # Add cache statistics
        cache_stats = query_cache.get_stats()
        
        # Add system statistics
        process = psutil.Process()
        system_stats = {
            "memory_mb": round(process.memory_info().rss / 1024 / 1024, 2),
            "cpu_percent": process.cpu_percent(),
            "threads": process.num_threads(),
            "uptime_seconds": round(time.time() - process.create_time(), 2)
        }
        
        # Update metrics gauges
        for store_name, store_data in status["database"].items():
            metrics.update_vector_store_size(
                store_name, 
                store_data.get("document_count", 0)
            )
        metrics.update_cache_size("L1", cache_stats["l1"]["size"])
        metrics.update_memory_usage(process.memory_info().rss)
        
        return StatusResponse(
            **status,
            cache_stats=cache_stats,
            system_stats=system_stats
        )
    except Exception as e:
        logger.error(f"Status check error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve system status.")


@app.get("/cache/stats")
async def get_cache_stats():
    """Get detailed cache statistics."""
    return query_cache.get_stats()


@app.delete("/cache/clear")
async def clear_cache():
    """Clear query cache."""
    query_cache.clear()
    return {"message": "Cache cleared successfully"}


@app.post("/query/stream")
async def stream_clinical_query(query: str, use_cache: bool = True):
    """
    Streaming response endpoint for better UX.
    Returns response as Server-Sent Events (SSE).
    
    Events:
    - start: Query received
    - progress: Processing stage updates  
    - content: Response content chunks
    - sources: Source citations
    - complete: Full response complete
    - error: Error occurred
    """
    from src.api.streaming import StreamingQueryHandler
    
    async def generate():
        start_time = time.time()
        
        try:
            # Check cache
            if use_cache:
                cached = query_cache.get(query)
                if cached:
                    yield {
                        "event": "start",
                        "data": json.dumps({
                            "query": query,
                            "from_cache": True
                        })
                    }
                    
                    # Stream cached response in chunks
                    chunks = cached["response"].split('\n\n')
                    for i, chunk in enumerate(chunks):
                        yield {
                            "event": "content",
                            "data": json.dumps({
                                "chunk": chunk,
                                "chunk_index": i,
                                "progress": (i + 1) / len(chunks)
                            })
                        }
                        await asyncio.sleep(0.02)
                    
                    yield {
                        "event": "complete",
                        "data": json.dumps({
                            "sources": cached["sources"],
                            "safety_level": cached["safety_level"],
                            "duration_ms": round((time.time() - start_time) * 1000, 2),
                            "from_cache": True
                        })
                    }
                    yield {"event": "done", "data": "[DONE]"}
                    return
            
            # Process query
            handler = StreamingQueryHandler(supervisor)
            async for chunk in handler.generate_stream(query):
                yield chunk
                
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield {
                "event": "error",
                "data": json.dumps({
                    "error": str(e),
                    "error_type": type(e).__name__
                })
            }
    
    import json
    import asyncio
    from sse_starlette.sse import EventSourceResponse
    
    return EventSourceResponse(
        generate(),
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.delete("/clear")
async def clear_system_data():
    """
    Wipes all clinical databases and resets conversation history.
    Use with caution.
    """
    try:
        supervisor.clear_all()
        return {"message": "All clinical stores and conversation history have been successfully cleared."}
    except Exception as e:
        logger.error(f"Clear data error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to clear system data.")


if __name__ == "__main__":
    import uvicorn
    # In production, this would be triggered via CLI (e.g., uvicorn backend.app.main:app)
    uvicorn.run(app, host="0.0.0.0", port=8000)
