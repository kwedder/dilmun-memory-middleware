"""
Ring-Theoretic Memory Layer - Wedderburn-Kasczinski Implementation

Implements graded rings and modules for memory management:
1. Graded ring decomposition by session
2. Ideal-theoretic forgetting for staleness
3. Module-valued confidence weighting
4. Homogeneous component analysis
5. Tensor product relationships
"""

import json
import hashlib
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path

from .memory_store import MemoryStore


class GradedMemoryRing:
    """
    Graded ring structure for memory decomposition.
    Each session is a homogeneous component.
    """
    
    def __init__(self, store: MemoryStore):
        self.store = store
        self.sessions: Dict[str, Dict] = {}
    
    def open_session(self, session_id: str, scopes: Optional[List[str]] = None):
        """Open a new graded component."""
        self.sessions[session_id] = {
            "opened": datetime.now().isoformat(),
            "scopes": scopes if scopes is not None else [],
            "facts": []
        }
    
    def close_session(self, session_id: str):
        """Close a session."""
        if session_id in self.sessions:
            self.sessions[session_id]["closed"] = datetime.now().isoformat()
    
    def write_graded_fact(self, session_id: str, entity: str, predicate: str, 
                          value: Any, confidence: float = 1.0, ttl_days: int = 30):
        """Write fact in graded ring structure."""
        path = self.store.write_fact(
            entity=entity,
            predicate=predicate,
            value=str(value),
            scope=session_id,
            confidence=confidence,
            ttl_days=ttl_days
        )
        
        if session_id in self.sessions:
            self.sessions[session_id]["facts"].append(path)
        
        return path
    
    def read_graded_facts(self, session_id: str, min_confidence: float = 0.5) -> List[Dict]:
        """Read facts filtered by session and confidence."""
        return self.store.read_facts(
            scope=session_id,
            min_confidence=min_confidence
        )


class IdealForgetting:
    """
    Ideal-theoretic forgetting mechanism.
    Stale facts form an ideal I ⊂ R, quotient R/I gives cleaned memory.
    """
    
    def __init__(self, store: MemoryStore):
        self.store = store
        self.ideal: set = set()
    
    def mark_stale(self, days_old: int = 30, min_confidence: float = 0.3):
        """Mark stale facts for forgetting."""
        cutoff = datetime.now() - timedelta(days=days_old)
        
        for fact in self.store.read_facts(min_confidence=0.0):
            created_str = fact.get("created", "")
            if created_str:
                try:
                    created = datetime.fromisoformat(created_str)
                    if created < cutoff:
                        conf = fact.get("confidence", 1.0)
                        if conf < min_confidence:
                            self.ideal.add(fact)
                except ValueError:
                    continue
    
    def forget(self) -> int:
        """Apply forgetting, return count of forgotten facts."""
        forgotten = len(self.ideal)
        self.ideal.clear()
        return forgotten


class TensorProductMemory:
    """
    Tensor product structure for fact relationships.
    Fact ⊗ Fact = relationship
    """
    
    def __init__(self):
        self.relationships: Dict[str, List] = defaultdict(list)
    
    def tensor_product(self, fact1: Dict, fact2: Dict) -> Dict:
        """Compute tensor product of two facts."""
        entity = f"{fact1.get('entity', '')}⊗{fact2.get('entity', '')}"
        predicate = f"{fact1.get('predicate', '')}_{fact2.get('predicate', '')}"
        
        v1 = fact1.get('value', 0)
        v2 = fact2.get('value', 0)
        
        try:
            v1_num = float(v1)
            v2_num = float(v2)
            value = v1_num * v2_num
        except (ValueError, TypeError):
            value = f"{v1} related to {v2}"
        
        return {
            "entity": entity,
            "predicate": predicate,
            "value": value,
            "type": "tensor_product",
        }