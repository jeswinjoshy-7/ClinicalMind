"""
ClinicalMind Monitoring Layer

Prometheus metrics and structured logging for observability.

Metrics tracked:
- Query count and latency
- Cache hit/miss rates
- Tool execution times
- LLM API calls and tokens
- Error rates
- Active connections

Usage:
    from src.monitoring.metrics import metrics, track_operation
    
    with track_operation("query_processing"):
        result = process_query(query)
    
    metrics.QUERY_COUNT.labels(status="success").inc()
"""

import time
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime
from contextlib import contextmanager
from enum import Enum
import threading

from prometheus_client import Counter, Histogram, Gauge, generate_latest
CONTENT_TYPE = "text/plain; version=0.0.4"


# Prometheus Metrics Definitions
class ClinicalMindMetrics:
    """Prometheus metrics for ClinicalMind."""
    
    def __init__(self):
        # Query metrics
        self.QUERY_COUNT = Counter(
            'clinicalmind_queries_total',
            'Total number of queries processed',
            ['status', 'safety_level', 'from_cache']
        )
        
        self.QUERY_LATENCY = Histogram(
            'clinicalmind_query_latency_seconds',
            'Query latency in seconds',
            buckets=[0.1, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 30.0, 60.0]
        )
        
        self.QUERY_RESPONSE_LENGTH = Histogram(
            'clinicalmind_response_length_chars',
            'Response length in characters',
            buckets=[100, 500, 1000, 2000, 5000, 10000]
        )
        
        # Cache metrics
        self.CACHE_OPERATIONS = Counter(
            'clinicalmind_cache_operations_total',
            'Cache operations',
            ['operation', 'level', 'result']
        )
        
        self.CACHE_SIZE = Gauge(
            'clinicalmind_cache_size',
            'Current cache size',
            ['level']
        )
        
        # Retrieval metrics
        self.RETRIEVAL_COUNT = Counter(
            'clinicalmind_retrievals_total',
            'Total retrievals',
            ['store_name', 'status']
        )
        
        self.RETRIEVAL_LATENCY = Histogram(
            'clinicalmind_retrieval_latency_seconds',
            'Retrieval latency in seconds',
            buckets=[0.01, 0.05, 0.1, 0.2, 0.5, 1.0]
        )
        
        self.DOCUMENTS_RETRIEVED = Histogram(
            'clinicalmind_documents_retrieved',
            'Number of documents retrieved per query',
            buckets=[1, 2, 3, 4, 5, 10, 15, 20]
        )
        
        self.RETRIEVAL_SCORES = Histogram(
            'clinicalmind_retrieval_scores',
            'Retrieval similarity scores',
            buckets=[0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95]
        )
        
        # LLM metrics
        self.LLM_CALL_COUNT = Counter(
            'clinicalmind_llm_calls_total',
            'Total LLM calls',
            ['model', 'status']
        )
        
        self.LLM_TOKENS = Histogram(
            'clinicalmind_llm_tokens',
            'LLM tokens used per call',
            buckets=[100, 500, 1000, 2000, 4000, 8000, 16000]
        )
        
        self.LLM_LATENCY = Histogram(
            'clinicalmind_llm_latency_seconds',
            'LLM call latency in seconds',
            buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
        )
        
        self.LLM_COST = Counter(
            'clinicalmind_llm_cost_usd',
            'Total LLM cost in USD',
            ['model']
        )
        
        # Tool metrics
        self.TOOL_CALL_COUNT = Counter(
            'clinicalmind_tool_calls_total',
            'Total tool calls',
            ['tool_name', 'status']
        )
        
        self.TOOL_LATENCY = Histogram(
            'clinicalmind_tool_latency_seconds',
            'Tool call latency in seconds',
            buckets=[0.01, 0.05, 0.1, 0.2, 0.5, 1.0]
        )
        
        # Safety metrics
        self.SAFETY_CHECK_COUNT = Counter(
            'clinicalmind_safety_checks_total',
            'Total safety checks',
            ['risk_level', 'action']
        )
        
        # Error metrics
        self.ERROR_COUNT = Counter(
            'clinicalmind_errors_total',
            'Total errors',
            ['error_type', 'endpoint']
        )
        
        # Active connections gauge
        self.ACTIVE_CONNECTIONS = Gauge(
            'clinicalmind_active_connections',
            'Number of active connections'
        )
        
        # System metrics
        self.VECTOR_STORE_SIZE = Gauge(
            'clinicalmind_vectorstore_size',
            'Number of documents in vector store',
            ['store_name']
        )
        
        self.MEMORY_USAGE = Gauge(
            'clinicalmind_memory_usage_bytes',
            'Current memory usage in bytes'
        )
    
    def track_query(self, status: str, safety_level: str, from_cache: bool,
                   latency: float, response_length: int):
        """Track a complete query."""
        self.QUERY_COUNT.labels(
            status=status,
            safety_level=safety_level,
            from_cache="true" if from_cache else "false"
        ).inc()
        
        self.QUERY_LATENCY.observe(latency)
        self.QUERY_RESPONSE_LENGTH.observe(response_length)
    
    def track_cache_operation(self, operation: str, level: str, result: str):
        """Track cache operation."""
        self.CACHE_OPERATIONS.labels(
            operation=operation,
            level=level,
            result=result
        ).inc()
    
    def track_retrieval(self, store_name: str, status: str, latency: float,
                       num_docs: int, avg_score: float):
        """Track retrieval operation."""
        self.RETRIEVAL_COUNT.labels(
            store_name=store_name,
            status=status
        ).inc()
        
        self.RETRIEVAL_LATENCY.observe(latency)
        self.DOCUMENTS_RETRIEVED.observe(num_docs)
        self.RETRIEVAL_SCORES.observe(avg_score)
    
    def track_llm_call(self, model: str, status: str, tokens: int,
                      latency: float, cost: float = 0.0):
        """Track LLM API call."""
        self.LLM_CALL_COUNT.labels(
            model=model,
            status=status
        ).inc()
        
        self.LLM_TOKENS.observe(tokens)
        self.LLM_LATENCY.observe(latency)
        
        if cost > 0:
            self.LLM_COST.labels(model=model).inc(cost)
    
    def track_tool_call(self, tool_name: str, status: str, latency: float):
        """Track tool execution."""
        self.TOOL_CALL_COUNT.labels(
            tool_name=tool_name,
            status=status
        ).inc()
        
        self.TOOL_LATENCY.observe(latency)
    
    def track_safety_check(self, risk_level: str, action: str):
        """Track safety check."""
        self.SAFETY_CHECK_COUNT.labels(
            risk_level=risk_level,
            action=action
        ).inc()
    
    def track_error(self, error_type: str, endpoint: str):
        """Track error."""
        self.ERROR_COUNT.labels(
            error_type=error_type,
            endpoint=endpoint
        ).inc()
    
    def update_cache_size(self, level: str, size: int):
        """Update cache size gauge."""
        self.CACHE_SIZE.labels(level=level).set(size)
    
    def update_vector_store_size(self, store_name: str, size: int):
        """Update vector store size gauge."""
        self.VECTOR_STORE_SIZE.labels(store_name=store_name).set(size)
    
    def update_memory_usage(self, bytes: int):
        """Update memory usage gauge."""
        self.MEMORY_USAGE.set(bytes)
    
    def inc_active_connections(self):
        """Increment active connections."""
        self.ACTIVE_CONNECTIONS.inc()
    
    def dec_active_connections(self):
        """Decrement active connections."""
        self.ACTIVE_CONNECTIONS.dec()


# Global metrics instance
metrics = ClinicalMindMetrics()


@contextmanager
def track_operation(operation_name: str, labels: Dict[str, str] = None):
    """
    Context manager to track operation timing and errors.
    
    Usage:
        with track_operation("query_processing", {"user": "admin"}):
            result = process_query(query)
    """
    start_time = time.time()
    success = True
    error_type = None
    
    try:
        yield
    except Exception as e:
        success = False
        error_type = type(e).__name__
        raise
    finally:
        duration = time.time() - start_time
        
        # Log timing
        logging.info(json.dumps({
            "event": "operation_timing",
            "operation": operation_name,
            "duration_ms": round(duration * 1000, 2),
            "success": success,
            "error_type": error_type,
            "labels": labels or {},
            "timestamp": datetime.now().isoformat()
        }))
        
        # Track error if failed
        if not success and error_type:
            metrics.track_error(error_type, operation_name)


# Structured Logger
class ClinicalMindLogger:
    """
    Structured logger for ClinicalMind.
    Outputs JSON-formatted logs for easy parsing.
    """
    
    def __init__(self, name: str = "ClinicalMind", log_file: str = None):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # JSON formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        ch.setFormatter(formatter)
        
        # File handler (optional)
        if log_file:
            fh = logging.FileHandler(log_file)
            fh.setLevel(logging.INFO)
            fh.setFormatter(formatter)
            self.logger.addHandler(fh)
        
        self.logger.addHandler(ch)
    
    def _log(self, level: str, event: str, **kwargs):
        """Internal log method with JSON formatting."""
        log_entry = {
            "event": event,
            "timestamp": datetime.now().isoformat(),
            **kwargs
        }
        getattr(self.logger, level)(json.dumps(log_entry))
    
    def log_query(self, query: str, response: str, sources: List[str],
                 risk_level: str, duration_ms: float, from_cache: bool = False):
        """Log a complete query."""
        self._log(
            "info",
            "query_complete",
            query_preview=query[:100],
            response_length=len(response),
            sources_count=len(sources),
            risk_level=risk_level,
            duration_ms=round(duration_ms, 2),
            from_cache=from_cache
        )
    
    def log_tool_call(self, tool_name: str, args: Dict[str, Any],
                     result_preview: str, duration_ms: float, success: bool = True):
        """Log tool execution."""
        event_type = "tool_success" if success else "tool_error"
        self._log(
            "info" if success else "error",
            event_type,
            tool_name=tool_name,
            args_keys=list(args.keys()),
            result_preview=result_preview[:200] if result_preview else None,
            duration_ms=round(duration_ms, 2)
        )
    
    def log_retrieval(self, store_name: str, query: str, num_results: int,
                     avg_score: float, duration_ms: float):
        """Log retrieval operation."""
        self._log(
            "info",
            "retrieval",
            store_name=store_name,
            query_preview=query[:50],
            num_results=num_results,
            avg_score=round(avg_score, 3),
            duration_ms=round(duration_ms, 2)
        )
    
    def log_llm_call(self, model: str, prompt_tokens: int, completion_tokens: int,
                    duration_ms: float, cost_usd: float = 0.0, status: str = "success"):
        """Log LLM API call."""
        self._log(
            "info" if status == "success" else "error",
            "llm_call",
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            duration_ms=round(duration_ms, 2),
            cost_usd=round(cost_usd, 6),
            status=status
        )
    
    def log_cache_operation(self, operation: str, level: str, result: str,
                          query_preview: str = None):
        """Log cache operation."""
        self._log(
            "debug",
            "cache_operation",
            operation=operation,
            level=level,
            result=result,
            query_preview=query_preview[:50] if query_preview else None
        )
    
    def log_error(self, error_type: str, message: str, endpoint: str = None,
                 query: str = None):
        """Log error."""
        self._log(
            "error",
            "error",
            error_type=error_type,
            message=message,
            endpoint=endpoint,
            query_preview=query[:100] if query else None
        )
    
    def log_safety_check(self, risk_level: str, action: str, keywords: List[str] = None):
        """Log safety check."""
        self._log(
            "info",
            "safety_check",
            risk_level=risk_level,
            action=action,
            keywords_detected=keywords or []
        )


# Global logger instance
logger = ClinicalMindLogger()


# FastAPI middleware for request tracking
class MonitoringMiddleware:
    """
    FastAPI middleware for automatic request monitoring.
    Tracks latency, errors, and active connections.
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        
        # Track active connections
        metrics.inc_active_connections()
        
        start_time = time.time()
        path = scope.get('path', 'unknown')
        
        try:
            async def send_wrapper(message):
                if message['type'] == 'http.response.start':
                    status_code = message['status']
                    duration = time.time() - start_time
                    
                    # Log request
                    logger.logger.info(json.dumps({
                        "event": "http_request",
                        "path": path,
                        "status_code": status_code,
                        "duration_ms": round(duration * 1000, 2),
                        "timestamp": datetime.now().isoformat()
                    }))
                    
                    # Track errors
                    if status_code >= 500:
                        metrics.track_error(f"http_{status_code}", path)
                
                await send(message)
            
            return await self.app(scope, receive, send_wrapper)
            
        finally:
            metrics.dec_active_connections()


def get_metrics_endpoint():
    """
    Create FastAPI endpoint for Prometheus metrics.
    
    Usage in FastAPI app:
        from src.monitoring.metrics import get_metrics_endpoint
        app.add_api_route("/metrics", get_metrics_endpoint(), methods=["GET"])
    """
    from fastapi.responses import Response
    
    def metrics_endpoint():
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE
        )
    
    return metrics_endpoint
