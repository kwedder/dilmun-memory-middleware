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

The middleware implements **graded rings** with the following mathematical structure:

### Graded Ring Decomposition (R = ⊕ₙ Rₙ)

Each session (episode) forms a **homogeneous component** Rₙ in the graded ring:

```
R = R₀ ⊕ R₁ ⊕ R₂ ⊕ ... ⊕ Rₙ

Where:
- R₀ = Global facts (accessible across all sessions)
- R₁ = Session 1 facts
- R₂ = Session 2 facts
- ...
```

This allows natural session isolation and controlled information flow between contexts.

### Ideal-Theoretic Forgetting (R/I)

Stale facts form an **ideal** I ⊂ R. The quotient ring R/I represents memory after forgetting:

```
I = {facts | age(f) > threshold OR confidence(f) < min_confidence}
R/I = R with stale facts "collapsed away"
```

This is the mathematical foundation for automatic forgetting - facts in the ideal are systematically removed via the quotient operation.

### Module-Valued Confidence

Each fact has a **confidence weight** c ∈ [0,1] representing reliability. This acts as a scalar multiplication on the free module:

```
c · fact ≡ fact with weight c

Operations:
- Fact comparison: c₁ · f₁ + c₂ · f₂ → weighted average
- Confidence propagation: confidence propagates through tensor products
```

### Wedderburn-Kasczinski Conflict Resolution

When two facts conflict (same entity, predicate, different values), temporal ordering resolves:

```
fact₁ = (e, p, v₁, t₁)
fact₂ = (e, p, v₂, t₂)

If t₂ > t₁: fact₂ is canonical, fact₁ ∈ I (ideal for resolution)
```

This implements the Wedderburn-Kasczski theorem: in a semisimple ring, conflicting elements can be resolved by selecting the "newest" representative under the ring's natural grading.

### Tensor Product Relationships (Fact ⊗ Fact → Relationship)

Two facts can form a relationship via tensor product:

```
f₁ ⊗ f₂ = relationship(f₁.entity, f₂.entity, f₁.predicate, f₂.predicate)
```

This enables automatic inference and connection discovery between related facts.

## Development

```bash
pip install -e .
python -m pytest tests/
```

## License

MIT
