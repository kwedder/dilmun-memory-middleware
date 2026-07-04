"""
Dilmun Memory Middleware

A deterministic, algebraically structured memory system for persistent
AI agents. Memory is a structured algebraic object: a finite set of
immutable facts f = (e, p, v, t, ν) governed by deterministic operators
for canonicalization, forgetting, composition, and retrieval.

Example:
    from dilmun import DilmunMemory

    memory = DilmunMemory("./vault")
    memory.open_episode("chat_001")
    memory.write_fact(entity="user", predicate="favorite_color",
                      value="blue", confidence=0.95)
    context = memory.get_context()
    memory.close_episode()
"""

__version__ = "0.2.0"

from .fact import Fact
from .memory import DilmunMemory
from .operators import (
    build_graph,
    canonicalize,
    compose,
    composable,
    degree_centrality,
    derive,
    forget,
    retrieve,
    score_facts,
)
from .backends import Backend, JSONVault, SQLiteBackend

# Legacy markdown-vault store and its compression pipeline.
from .memory_store import MemoryStore
from .compression import compress_notes, CompressionError

# Deprecated alias kept for pre-0.2 imports.
DilmunMemoryMiddleware = DilmunMemory

__all__ = [
    "DilmunMemory",
    "Fact",
    "canonicalize",
    "forget",
    "compose",
    "composable",
    "derive",
    "retrieve",
    "score_facts",
    "build_graph",
    "degree_centrality",
    "Backend",
    "JSONVault",
    "SQLiteBackend",
    "MemoryStore",
    "compress_notes",
    "CompressionError",
    "DilmunMemoryMiddleware",
]
