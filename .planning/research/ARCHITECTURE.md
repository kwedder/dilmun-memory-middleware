# Architecture Research

## Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                    DilmunMemoryMiddleware                    │
├─────────────────────────────────────────────────────────────┤
│  GradedMemoryRing  │  IdealForgetting  │  TensorProduct     │
│  (sessions)        │  (stale facts)    │  (relationships)   │
├─────────────────────────────────────────────────────────────┤
│                    MemoryStore (file-based)                 │
│  fact/      decision/  episode/  conflict/  compressed/     │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

1. **Write**: Fact → check conflict → resolve via temporal ordering → store
2. **Read**: Filter by scope → weight by confidence → return
3. **Forget**: Mark stale → form ideal → quotient ring → delete

## Build Order

1. **Phase 1**: MemoryStore (basic persistence)
2. **Phase 2**: GradedMemoryRing (session management)
3. **Phase 3**: Conflict resolution (Wedderburn-Kasczinski)
4. **Phase 4**: Memory compression (3-strand)

---
*Research: Architecture dimension*
