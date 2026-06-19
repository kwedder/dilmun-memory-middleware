# Dilmun Memory Middleware

A Python library for AI agents to maintain persistent, structured memory that transcends context windows. Uses ring-theoretic mathematics for automatic conflict resolution and forgetting.

## The Problem

AI agents lose context between sessions. Traditional approaches either:

- Fit everything in expensive context windows
- Lose important information between runs

## The Solution

Dilmun Memory Middleware stores memory as structured facts that persist across sessions. It uses novel ring-theoretic mathematics to:

- Automatically resolve conflicts via temporal ordering
- Forget stale facts via ideal-theoretic quotients
- Weight facts by confidence for reliable recall

## Quick Start

```python
from dilmun import DilmunMemoryMiddleware

# Initialize
middleware = DilmunMemoryMiddleware(vault_path="./memory")

# Open a session
middleware.open_episode("chat_123", ["conversation", "user_preference"])

# Store facts
middleware.write_fact("user", "name", "Alice")
middleware.write_fact("user", "preference", "blue", confidence=0.9)

# Retrieve context
facts = middleware.get_context()

# Close session
middleware.close_episode()
```

## Features

- **Entity-Predicate-Value Facts**: Structured memory storage
- **Session Scoping**: Episode contexts for isolation
- **Conflict Resolution**: Wedderburn-Kasczinski temporal ordering
- **Confidence Weighting**: Module-valued fact reliability
- **Automatic Forgetting**: Ideal-theoretic stale fact removal

## Ring Theory

The middleware implements graded rings where:

- Each session is a homogeneous component
- Stale facts form an ideal that's quotiented out
- Confidence weights are module scalars

This provides mathematically sound memory management without ad-hoc heuristics.

## Development

```bash
pip install -e .
python -m pytest tests/
```

## License

MIT
