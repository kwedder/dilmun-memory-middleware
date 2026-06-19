# Stack Research

## Python Ecosystem

**Core Dependencies:**

- Python 3.10+ (dataclasses, pathlib, hashlib built-in)
- No external ML dependencies (minimal barrier to entry)

**Memory Storage:**

- File-based JSON (Obsidian vault compatible)
- Front-matter structure for metadata
- Hash-based deterministic IDs

**Ring Theory Implementation:**

- `GradedMemoryRing` - Session decomposition
- `IdealForgetting` - Stale fact removal  
- `TensorProductMemory` - Fact relationships
- `WedderburnKasczinski` - Conflict resolution

## Alternative Approaches

| Approach | Pros | Cons |
|----------|------|------|
| Redis/Memcached | Fast, proven | External dependency, loses structure |
| SQLite | Structured, ACID | Schema rigidity |
| Neo4j | Graph relationships | Heavy, complex setup |
| Chroma/Weaviate | Vector search | ML dependencies |

## Recommendation

**Standalone library with minimal dependencies:**

- Core: `ring_memory.py` (pure Python)
- Optional: `memory_store.py` adapter for persistence
- Optional: Vector search via `numpy` (not required)

---
*Research: Stack dimension*
