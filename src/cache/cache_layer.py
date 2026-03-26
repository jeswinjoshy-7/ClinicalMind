"""
ClinicalMind Cache Layer

Multi-level caching system for query results and embeddings.
- L1: In-memory cache (fastest, limited size)
- L2: Redis cache (shared across instances, persistent)

Usage:
    from src.cache.cache_layer import QueryCache, EmbeddingCache
    
    query_cache = QueryCache()
    result = query_cache.get(query)
    if not result:
        result = generate_response(query)
        query_cache.set(query, result)
"""

import hashlib
import json
import time
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
import threading

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cached query result."""
    query_hash: str
    response: str
    sources: List[str]
    safety_level: str
    created_at: float
    ttl: int  # Time to live in seconds
    hit_count: int = 0
    
    def is_expired(self) -> bool:
        return time.time() > (self.created_at + self.ttl)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_hash": self.query_hash,
            "response": self.response,
            "sources": self.sources,
            "safety_level": self.safety_level,
            "created_at": self.created_at,
            "ttl": self.ttl,
            "hit_count": self.hit_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CacheEntry":
        return cls(**data)


class InMemoryCache:
    """
    L1 In-memory cache with LRU eviction.
    Thread-safe for concurrent access.
    """
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: List[str] = []
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0
    
    def get(self, query: str) -> Optional[CacheEntry]:
        """Get cached result for query."""
        query_hash = self._compute_hash(query)
        
        with self._lock:
            if query_hash in self._cache:
                entry = self._cache[query_hash]
                if not entry.is_expired():
                    # Update access order (LRU)
                    self._access_order.remove(query_hash)
                    self._access_order.append(query_hash)
                    entry.hit_count += 1
                    self._hits += 1
                    logger.debug(f"Cache hit for query: {query[:50]}...")
                    return entry
                else:
                    # Remove expired entry
                    del self._cache[query_hash]
                    self._access_order.remove(query_hash)
            
            self._misses += 1
            return None
    
    def set(self, query: str, response: str, sources: List[str], 
            safety_level: str, ttl: Optional[int] = None):
        """Cache a query result."""
        query_hash = self._compute_hash(query)
        entry = CacheEntry(
            query_hash=query_hash,
            response=response,
            sources=sources,
            safety_level=safety_level,
            created_at=time.time(),
            ttl=ttl or self.default_ttl
        )
        
        with self._lock:
            # Evict if over capacity (LRU)
            if len(self._cache) >= self.max_size:
                self._evict_oldest()
            
            self._cache[query_hash] = entry
            self._access_order.append(query_hash)
            logger.debug(f"Cached query: {query[:50]}...")
    
    def _evict_oldest(self):
        """Evict oldest cache entry (LRU)."""
        if self._access_order:
            oldest_hash = self._access_order.pop(0)
            if oldest_hash in self._cache:
                del self._cache[oldest_hash]
                logger.debug(f"Evicted oldest cache entry: {oldest_hash}")
    
    def _compute_hash(self, query: str) -> str:
        """Compute deterministic hash for query."""
        normalized = " ".join(query.lower().strip().split())
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]
    
    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
            logger.info("In-memory cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            valid_entries = sum(
                1 for entry in self._cache.values() 
                if not entry.is_expired()
            )
            total_requests = self._hits + self._misses
            hit_rate = self._hits / total_requests if total_requests > 0 else 0
            
            return {
                "size": valid_entries,
                "max_size": self.max_size,
                "utilization": valid_entries / self.max_size if self.max_size > 0 else 0,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": hit_rate,
                "ttl_seconds": self.default_ttl
            }


class RedisCache:
    """
    L2 Redis cache for distributed caching.
    Falls back gracefully if Redis is unavailable.
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379", 
                 default_ttl: int = 3600):
        self.default_ttl = default_ttl
        self._redis = None
        self._available = False
        
        try:
            import redis
            self._redis = redis.from_url(redis_url, socket_timeout=2)
            self._redis.ping()
            self._available = True
            logger.info("Redis cache connected")
        except Exception as e:
            logger.warning(f"Redis not available, caching disabled: {e}")
    
    def get(self, query_hash: str) -> Optional[CacheEntry]:
        """Get cached result by hash."""
        if not self._available or not self._redis:
            return None
        
        try:
            cached = self._redis.get(f"clinicalmind:query:{query_hash}")
            if cached:
                entry = CacheEntry.from_dict(json.loads(cached))
                if not entry.is_expired():
                    return entry
                else:
                    self._redis.delete(f"clinicalmind:query:{query_hash}")
        except Exception as e:
            logger.warning(f"Redis get error: {e}")
        
        return None
    
    def set(self, query_hash: str, entry: CacheEntry):
        """Set cached result by hash."""
        if not self._available or not self._redis:
            return
        
        try:
            self._redis.setex(
                f"clinicalmind:query:{query_hash}",
                entry.ttl,
                json.dumps(entry.to_dict())
            )
        except Exception as e:
            logger.warning(f"Redis set error: {e}")
    
    def clear(self):
        """Clear all cache entries."""
        if not self._available or not self._redis:
            return
        
        try:
            keys = self._redis.keys("clinicalmind:query:*")
            if keys:
                self._redis.delete(*keys)
                logger.info("Redis cache cleared")
        except Exception as e:
            logger.warning(f"Redis clear error: {e}")
    
    def is_available(self) -> bool:
        return self._available


class QueryCache:
    """
    Multi-level query cache combining L1 (in-memory) and L2 (Redis).
    
    Strategy:
    - Check L1 first (fastest)
    - If miss, check L2
    - If miss, compute and store in both L1 and L2
    """
    
    def __init__(
        self,
        l1_max_size: int = 1000,
        l1_ttl: int = 1800,  # 30 minutes
        l2_ttl: int = 3600,  # 1 hour
        redis_url: str = "redis://localhost:6379"
    ):
        self.l1_cache = InMemoryCache(max_size=l1_max_size, default_ttl=l1_ttl)
        self.l2_cache = RedisCache(redis_url=redis_url, default_ttl=l2_ttl)
        self._lock = threading.RLock()
    
    def get(self, query: str) -> Optional[Dict[str, Any]]:
        """Get cached query result."""
        # Check L1 cache first
        l1_entry = self.l1_cache.get(query)
        if l1_entry:
            return {
                "response": l1_entry.response,
                "sources": l1_entry.sources,
                "safety_level": l1_entry.safety_level,
                "from_cache": True,
                "cache_level": "L1"
            }
        
        # Check L2 cache
        query_hash = self._compute_hash(query)
        l2_entry = self.l2_cache.get(query_hash)
        if l2_entry:
            # Promote to L1 cache
            with self._lock:
                self.l1_cache.set(
                    query,
                    l2_entry.response,
                    l2_entry.sources,
                    l2_entry.safety_level,
                    l2_entry.ttl
                )
            
            return {
                "response": l2_entry.response,
                "sources": l2_entry.sources,
                "safety_level": l2_entry.safety_level,
                "from_cache": True,
                "cache_level": "L2"
            }
        
        return None
    
    def set(
        self,
        query: str,
        response: str,
        sources: List[str],
        safety_level: str,
        ttl: Optional[int] = None
    ):
        """Cache a query result in both L1 and L2."""
        query_hash = self._compute_hash(query)
        
        with self._lock:
            # Store in L1
            self.l1_cache.set(query, response, sources, safety_level, ttl)
            
            # Store in L2
            entry = CacheEntry(
                query_hash=query_hash,
                response=response,
                sources=sources,
                safety_level=safety_level,
                created_at=time.time(),
                ttl=ttl or self.l2_cache.default_ttl
            )
            self.l2_cache.set(query_hash, entry)
    
    def _compute_hash(self, query: str) -> str:
        normalized = " ".join(query.lower().strip().split())
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]
    
    def clear(self):
        """Clear both cache levels."""
        self.l1_cache.clear()
        self.l2_cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get combined cache statistics."""
        l1_stats = self.l1_cache.get_stats()
        
        return {
            "l1": l1_stats,
            "l2": {
                "available": self.l2_cache.is_available(),
                "ttl_seconds": self.l2_cache.default_ttl
            },
            "total_size": l1_stats["size"],
            "hit_rate": l1_stats["hit_rate"]
        }


class EmbeddingCache:
    """
    Cache for embeddings to avoid recomputation.
    Useful when re-indexing documents.
    """
    
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self._cache: Dict[str, Any] = {}
        self._order: List[str] = []
        self._lock = threading.RLock()
    
    def _compute_hash(self, text: str) -> str:
        normalized = " ".join(text.lower().strip().split())
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]
    
    def get(self, text: str) -> Optional[Any]:
        text_hash = self._compute_hash(text)
        
        with self._lock:
            return self._cache.get(text_hash)
    
    def set(self, text: str, embedding: Any):
        text_hash = self._compute_hash(text)
        
        with self._lock:
            self._cache[text_hash] = embedding
            self._order.append(text_hash)
            
            # Evict if over capacity
            if len(self._cache) > self.max_size:
                oldest = self._order.pop(0)
                del self._cache[oldest]
    
    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "utilization": len(self._cache) / self.max_size
            }


# Singleton instance for project-wide use
_query_cache: Optional[QueryCache] = None
_embedding_cache: Optional[EmbeddingCache] = None


def get_query_cache() -> QueryCache:
    """Get or create singleton query cache instance."""
    global _query_cache
    if _query_cache is None:
        _query_cache = QueryCache()
    return _query_cache


def get_embedding_cache() -> EmbeddingCache:
    """Get or create singleton embedding cache instance."""
    global _embedding_cache
    if _embedding_cache is None:
        _embedding_cache = EmbeddingCache()
    return _embedding_cache
