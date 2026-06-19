"""
Dilmun Memory Middleware - Unified interface for ring-theoretic memory.

Combines memory store, graded rings, ideal forgetting, and tensor products
into a single coherent API.
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from .memory_store import MemoryStore
from .ring_memory import GradedMemoryRing, IdealForgetting, TensorProductMemory


class DilmunMemoryMiddleware:
    """
    Unified memory middleware for AI agents.
    
    Provides persistent, structured memory that transcends context windows
    using ring-theoretic mathematics for automatic conflict resolution.
    """
    
    def __init__(self, vault_path: Optional[str] = None):
        """Initialize middleware with optional vault path."""
        self.vault_path = Path(vault_path or os.environ.get(
            "DILMUN_VAULT", "./memory"
        ))
        self.store = MemoryStore(str(self.vault_path))
        self.ring = GradedMemoryRing(self.store)
        self.forgetting = IdealForgetting(self.store)
        self.tensor = TensorProductMemory()
        self._current_episode: Optional[str] = None
    
    def open_episode(self, episode_id: str, scopes: Optional[List[str]] = None):
        """Open a new episode (session context)."""
        self.ring.open_session(episode_id, scopes)
        self._current_episode = episode_id
    
    def close_episode(self):
        """Close the current episode."""
        if self._current_episode:
            self.ring.close_session(self._current_episode)
            self._current_episode = None
    
    def write_fact(self, entity: str, predicate: str, value: Any,
                   scope: Optional[str] = None, confidence: float = 1.0,
                   ttl_days: int = 30) -> str:
        """Store a fact with entity-predicate-value structure."""
        return self.store.write_fact(
            entity=entity,
            predicate=predicate,
            value=value,
            scope=scope or self._current_episode,
            confidence=confidence,
            ttl_days=ttl_days
        )
    
    def read_facts(self, entity: Optional[str] = None, 
                   predicate: Optional[str] = None,
                   scope: Optional[str] = None,
                   min_confidence: float = 0.0) -> List[Dict]:
        """Retrieve facts with optional filtering."""
        return self.store.read_facts(
            entity=entity,
            predicate=predicate,
            scope=scope or self._current_episode,
            min_confidence=min_confidence
        )
    
    def get_context(self, max_facts: int = 100) -> List[Dict]:
        """Get current episode context."""
        if not self._current_episode:
            return []
        return self.ring.read_graded_facts(
            self._current_episode, min_confidence=0.0
        )[:max_facts]
    
    def auto_forget(self, days_old: int = 30, min_confidence: float = 0.3) -> int:
        """Run automatic forgetting of stale facts."""
        self.forgetting.mark_stale(days_old=days_old, min_confidence=min_confidence)
        return self.forgetting.forget()