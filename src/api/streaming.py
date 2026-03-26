"""
ClinicalMind Streaming API

Server-Sent Events (SSE) streaming for real-time response delivery.

Usage:
    @app.get("/query/stream")
    async def stream_query(query: str):
        return StreamingResponse(
            generate_stream(query),
            media_type="text/event-stream"
        )
"""

import json
import time
import asyncio
import logging
from typing import AsyncGenerator, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

from fastapi.responses import StreamingResponse
from fastapi import Request
from sse_starlette.sse import EventSourceResponse

logger = logging.getLogger(__name__)


@dataclass
class StreamChunk:
    """A single chunk of streamed response."""
    chunk_type: str  # 'start', 'content', 'source', 'end', 'error'
    content: str
    metadata: Dict[str, Any] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_type": self.chunk_type,
            "content": self.content,
            "metadata": self.metadata or {},
            "timestamp": self.timestamp
        }


class StreamingQueryHandler:
    """
    Handles streaming query execution with progress updates.
    """
    
    def __init__(self, supervisor):
        self.supervisor = supervisor
    
    async def generate_stream(self, query: str) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generate streaming response for a query.
        
        Yields:
            Dict with chunk_type, content, and metadata
        """
        start_time = time.time()
        
        try:
            # Send start event
            yield {
                "event": "start",
                "data": json.dumps({
                    "query": query,
                    "timestamp": datetime.now().isoformat()
                })
            }
            
            # Stage 1: Safety check
            yield {
                "event": "progress",
                "data": json.dumps({
                    "stage": "safety_check",
                    "message": "Checking query safety...",
                    "progress": 0.1
                })
            }
            
            query_safety = self.supervisor.safety_checker.check_content(query)
            
            yield {
                "event": "progress",
                "data": json.dumps({
                    "stage": "safety_check_complete",
                    "message": f"Safety level: {query_safety.risk_level.value}",
                    "progress": 0.2,
                    "safety_level": query_safety.risk_level.value
                })
            }
            
            # Stage 2: Retrieval
            yield {
                "event": "progress",
                "data": json.dumps({
                    "stage": "retrieval",
                    "message": "Searching knowledge base...",
                    "progress": 0.3
                })
            }
            
            # Stage 3: LLM Generation (stream tokens if possible)
            yield {
                "event": "progress",
                "data": json.dumps({
                    "stage": "generating",
                    "message": "Generating response...",
                    "progress": 0.5
                })
            }
            
            # Execute query
            result = self.supervisor.query(query)
            
            # Stream response in chunks
            response_text = result.answer
            chunks = self._split_into_chunks(response_text)
            
            for i, chunk in enumerate(chunks):
                yield {
                    "event": "content",
                    "data": json.dumps({
                        "chunk": chunk,
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "progress": 0.5 + (0.3 * (i + 1) / len(chunks))
                    })
                }
                # Small delay for streaming effect
                await asyncio.sleep(0.02)
            
            # Stage 4: Sources
            if result.sources:
                yield {
                    "event": "sources",
                    "data": json.dumps({
                        "sources": result.sources,
                        "count": len(result.sources)
                    })
                }
            
            # Stage 5: Complete
            duration_ms = (time.time() - start_time) * 1000
            
            yield {
                "event": "complete",
                "data": json.dumps({
                    "full_response": response_text,
                    "sources": result.sources,
                    "safety_level": result.risk_level,
                    "duration_ms": round(duration_ms, 2),
                    "timestamp": datetime.now().isoformat()
                })
            }
            
            # Send done marker
            yield {
                "event": "done",
                "data": "[DONE]"
            }
            
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield {
                "event": "error",
                "data": json.dumps({
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "timestamp": datetime.now().isoformat()
                })
            }
    
    def _split_into_chunks(self, text: str, chunk_size: int = 200) -> List[str]:
        """Split response into chunks for streaming."""
        chunks = []
        
        # Split by paragraphs first
        paragraphs = text.split('\n\n')
        current_chunk = ""
        
        for para in paragraphs:
            if len(current_chunk) + len(para) < chunk_size:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + "\n\n"
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        # Further split large chunks
        final_chunks = []
        for chunk in chunks:
            if len(chunk) > chunk_size * 2:
                # Split by sentences
                sentences = chunk.split('. ')
                current = ""
                for sentence in sentences:
                    if len(current) + len(sentence) < chunk_size:
                        current += sentence + ". "
                    else:
                        if current:
                            final_chunks.append(current.strip())
                        current = sentence + ". "
                if current.strip():
                    final_chunks.append(current.strip())
            else:
                final_chunks.append(chunk)
        
        return final_chunks if final_chunks else chunks


class TokenStreamingHandler:
    """
    Advanced streaming that streams individual tokens from LLM.
    Requires async LLM support.
    """
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
    
    async def stream_tokens(self, messages: List[Dict]) -> AsyncGenerator[str, None]:
        """
        Stream individual tokens from LLM.
        
        Note: This requires the LLM client to support streaming.
        For Groq, use the streaming API.
        """
        try:
            # For Groq streaming
            stream = self.llm_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                stream=True,
                max_tokens=2048
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    yield content
                    await asyncio.sleep(0.01)  # Small delay for UX
                    
        except Exception as e:
            logger.error(f"Token streaming error: {e}")
            yield f"[Error generating response: {str(e)}]"


# FastAPI endpoint functions

def create_streaming_endpoint(app, supervisor):
    """
    Create streaming query endpoint for FastAPI app.
    
    Usage:
        create_streaming_endpoint(app, supervisor)
    """
    from fastapi import Query
    
    handler = StreamingQueryHandler(supervisor)
    
    @app.get("/query/stream")
    async def stream_query(
        query: str = Query(..., description="Clinical query to process"),
        use_cache: bool = Query(True, description="Use cached results if available")
    ):
        """
        Stream clinical query response in real-time.
        
        Events:
        - start: Query received
        - progress: Processing stage updates
        - content: Response content chunks
        - sources: Source citations
        - complete: Full response complete
        - error: Error occurred
        """
        return EventSourceResponse(
            handler.generate_stream(query),
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Disable nginx buffering
            }
        )
    
    @app.get("/query/stream/token")
    async def stream_query_tokens(
        query: str = Query(..., description="Clinical query to process")
    ):
        """
        Stream individual tokens from LLM response.
        Provides smoother streaming experience.
        """
        from langchain_groq import ChatGroq
        from configs.config import settings
        
        llm = ChatGroq(
            temperature=0.1,
            groq_api_key=settings.GROQ_API_KEY,
            model_name=settings.llm.model_name
        )
        
        token_handler = TokenStreamingHandler(llm.client)
        
        # Build messages
        messages = [
            {"role": "system", "content": "You are a helpful clinical assistant."},
            {"role": "user", "content": query}
        ]
        
        async def generate():
            async for token in token_handler.stream_tokens(messages):
                yield {
                    "event": "token",
                    "data": json.dumps({"token": token})
                }
        
        return EventSourceResponse(
            generate(),
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive"
            }
        )


# SSE-compatible generator for simpler use
async def simple_stream_generator(query: str, supervisor) -> AsyncGenerator[str, None]:
    """
    Simple streaming generator for basic use cases.
    Yields SSE-formatted strings.
    """
    try:
        # Start
        yield f"data: {json.dumps({'type': 'start', 'query': query})}\n\n"
        
        # Process query
        result = supervisor.query(query)
        
        # Stream response word by word
        words = result.answer.split()
        for i, word in enumerate(words):
            yield f"data: {json.dumps({
                'type': 'content',
                'content': word + ' ',
                'progress': (i + 1) / len(words)
            })}\n\n"
            await asyncio.sleep(0.01)
        
        # Complete
        yield f"data: {json.dumps({
            'type': 'complete',
            'sources': result.sources,
            'safety_level': result.risk_level
        })}\n\n"
        
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
