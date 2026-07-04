# Dilmun Memory Middleware

A deterministic, algebraically structured memory system for persistent AI agents.

## Core Value

**AI agents with persistent, structured memory that transcends context windows.**

## Quick Start

```python
from dilmun import DilmunMemory

memory = DilmunMemory("./vault")
memory.open_episode("my_session")

# Store facts — immutable 5-tuples (entity, predicate, value, timestamp, confidence)
memory.write_fact("user", "name", "Alice")
memory.write_fact("user", "preference", "blue", confidence=0.9)

# Retrieve the scored, canonicalized context
context = memory.get_context()

# Close session
memory.close_episode()
```

## Architecture

```
┌──────────────────────────────────────────────────┐
│                   DilmunMemory                   │
├──────────────────────────────────────────────────┤
│  operators: normalize (N)    │ canonicalize (C)  │
│             forget (F)       │ merge             │
│             compose (comp)   │ retrieve (score)  │
├──────────────────────────────────────────────────┤
│  episodes: M = M0 (global) ∪ M1 ∪ ... ∪ Mk       │
├──────────────────────────────────────────────────┤
│  backends: JSONVault (default) │ SQLiteBackend   │
└──────────────────────────────────────────────────┘
```

## Features

- Immutable entity-predicate-value facts with confidence valuation
- Predicate normalization (default + registry) so paraphrases collapse to one fact
- Episode-partitioned memory with explicit cross-episode promotion
- Deterministic, idempotent canonicalization (timestamp > confidence > insertion order)
- Idempotent forgetting operator (expiry, low confidence, contradiction pressure)
- Commutative, associative merge of two memory states
- Relational (path) composition over the memory graph
- Structured retrieval scoring: confidence + recency + graph centrality
- Reproducible benchmark vs a TF-IDF vector-memory baseline (benchmarks/)

## Development

```bash
# Install
pip install -e .

# Run tests
pytest tests/
# or without pytest:
python tests/test_operators.py && python tests/test_memory.py
```

## Documentation

- [README.md](README.md) - The memory algebra, formal properties, and API
- [PROJECT.md](.planning/PROJECT.md) - Project context
- [REQUIREMENTS.md](.planning/REQUIREMENTS.md) - Detailed requirements
- [ROADMAP.md](.planning/ROADMAP.md) - Execution roadmap

## License

MIT
