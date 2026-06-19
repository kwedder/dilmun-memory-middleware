# Requirements: Dilmun Memory Middleware

**Defined:** 2026-06-18
**Core Value:** AI agents with persistent, structured memory that transcends context windows.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Memory Storage

- [ ] **MEM-01**: Store facts as entity-predicate-value with metadata
- [ ] **MEM-02**: Retrieve facts by entity, predicate, or scope
- [ ] **MEM-03**: Support TTL-based automatic expiration

### Session Management

- [ ] **SESS-01**: Open and close episodes (session contexts)
- [ ] **SESS-02**: Retrieve facts scoped to active episode
- [ ] **SESS-03**: Track episode purpose and active scopes

### Conflict Resolution

- [ ] **CONF-01**: Detect entity-predicate conflicts
- [ ] **CONF-02**: Resolve conflicts via temporal ordering (Wedderburn-Kasczinski)
- [ ] **CONF-03**: Track decisions for resolved conflicts

### Ring Theory

- [ ] **RING-01**: Implement graded ring decomposition
- [ ] **RING-02**: Implement ideal-theoretic forgetting
- [ ] **RING-03**: Support confidence-weighted facts (module scalars)

## v2 Requirements

Deferred to future release.

### Compression

- **COMP-01**: 3-strand memory compression (assertion/provenance/dissent)
- **COMP-02**: Conservation invariant checking

### Search

- **SEARCH-01**: Vector similarity search for facts
- **SEARCH-02**: Semantic query interface

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real-time sync | File-based only for v1 |
| Multi-agent memory | Single-agent focus |
| Image/audio memory | Text-first approach |
| SQL/NoSQL backends | File-based JSON only |

## Traceability

| Requirement | Phase | Status |
| ----------- | ----- | ------ |
| MEM-01 | Phase 1 | Pending |
| MEM-02 | Phase 1 | Pending |
| MEM-03 | Phase 2 | Pending |
| SESS-01 | Phase 2 | Pending |
| SESS-02 | Phase 2 | Pending |
| SESS-03 | Phase 2 | Pending |
| CONF-01 | Phase 3 | Pending |
| CONF-02 | Phase 3 | Pending |
| CONF-03 | Phase 3 | Pending |
| RING-01 | Phase 4 | Pending |
| RING-02 | Phase 4 | Pending |
| RING-03 | Phase 4 | Pending |

**Coverage:**

- v1 requirements: 13 total
- Mapped to phases: 13
- Unmapped: 0 ✓

---
*Requirements defined: 2026-06-18*
*Last updated: 2026-06-18 after initial definition*
