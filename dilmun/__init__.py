"""
Dilmun Memory Middleware

A Python library for AI agents to maintain persistent, structured memory
that transcends context windows. Uses ring-theoretic mathematics for
automatic conflict resolution and forgetting.

Example:
    from dilmun import DilmunMemoryMiddleware
    
    middleware = DilmunMemoryMiddleware(vault_path="./memory")
    middleware.open_episode("session_1", ["chat", "tasks"])
    middleware.write_fact("user", "name", "Alice")
    facts = middleware.get_context()
"""

__version__ = "0.1.0"

from .middleware import DilmunMemoryMiddleware
from .memory_store import MemoryStore
from .ring_memory import GradedMemoryRing, IdealForgetting, TensorProductMemory

__all__ = [
    "DilmunMemoryMiddleware",
    "MemoryStore",
    "GradedMemoryRing",
    "IdealForgetting",
    "TensorProductMemory",
]