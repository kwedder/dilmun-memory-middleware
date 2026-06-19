# Roadmap: Dilmun Memory Middleware

**4 phases** | **13 requirements** | All v1 requirements covered ✓

| #   | Phase           | Goal                           | Requirements    | Success Criteria |
| --- | --------------- | ------------------------------ | --------------- | ---------------- |
| 1   | Memory Storage  | Persistent fact storage        | MEM-01, MEM-02  | CRUD operations work |
| 2   | Session Mgmt    | Episode contexts               | MEM-03, SESS-01, SESS-02, SESS-03 | Episodes scope memory |
| 3   | Conflict Res    | Wedderburn-Kasczinski          | CONF-01, CONF-02, CONF-03 | Conflicts auto-resolve |
| 4   | Ring Theory     | Mathematical foundation        | RING-01, RING-02, RING-03 | Ring ops work |

## Phase Details

**Phase 1: Memory Storage**
Goal: Basic fact storage and retrieval
Requirements: MEM-01, MEM-02
Success criteria:

1. Write facts with entity-predicate-value structure
2. Read facts by entity, predicate, or scope
3. All operations complete in <100ms

**Phase 2: Session Management**
Goal: Episode-scoped memory with TTL
Requirements: MEM-03, SESS-01, SESS-02, SESS-03
Success criteria:

1. Open/close episodes
2. Scoped fact retrieval
3. Automatic expiration of stale facts

**Phase 3: Conflict Resolution**
Goal: Wedderburn-Kasczinski conflict handling
Requirements: CONF-01, CONF-02, CONF-03
Success criteria:

1. Detect entity-predicate conflicts
2. Resolve via temporal ordering
3. Track all decisions

**Phase 4: Ring Theory**
Goal: Full ring-theoretic memory
Requirements: RING-01, RING-02, RING-03
Success criteria:

1. Graded ring decomposition
2. Ideal-theoretic forgetting
3. Confidence-weighted retrieval

---
*Roadmap created: 2026-06-18*
