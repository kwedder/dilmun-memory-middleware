# Dilmun Memory Middleware

A Python library for AI agents to maintain persistent, structured memory that transcends context windows.

## Core Value

**AI agents with persistent, structured memory that transcends context windows.**

## Quick Start

```python
from dilmun import DilmunMemoryMiddleware

middleware = DilmunMemoryMiddleware(vault_path="./memory")
middleware.open_episode("my_session", ["chat", "tasks"])

# Store facts
middleware.write_fact("user", "name", "Alice")
middleware.write_fact("user", "preference", "blue", confidence=0.9)

# Retrieve facts
facts = middleware.get_context()

# Close session
middleware.close_episode()
```

## Architecture

```
┌─────────────────────────────────────────────┐
│            DilmunMemoryMiddleware            │
├─────────────────────────────────────────────┤
│  GradedMemoryRing  │  IdealForgetting       │
│  (sessions)        │  (stale facts)         │
├─────────────────────────────────────────────┤
│              MemoryStore (file-based)        │
│  fact/  decision/  episode/  conflict/       │
└─────────────────────────────────────────────┘
```

## Features

- Entity-predicate-value fact storage
- Session-scoped memory with TTL
- Wedderburn-Kasczinski conflict resolution
- Confidence-weighted retrieval
- Ring-theoretic forgetting

## Development

```bash
# Install
pip install -e .

# Run tests
pytest tests/

# CLI
python -m dilmun.cli --help
```

## Documentation

- [PROJECT.md](.planning/PROJECT.md) - Project context
- [REQUIREMENTS.md](.planning/REQUIREMENTS.md) - Detailed requirements
- [ROADMAP.md](.planning/ROADMAP.md) - Execution roadmap

## License

MIT
