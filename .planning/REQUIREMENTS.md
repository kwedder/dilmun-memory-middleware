# Requirements: Dilmun Memory Middleware

**Defined:** 2026-06-18
**Core Value:** AI agents with persistent, structured memory that transcends context windows.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Dependencies

- [x] **DEP-01**: Scripts import from correct package location - Phase 1 ✓
- [x] **DEP-02**: All dependencies install without errors - Phase 1 ✓

### Paths

- [x] **PATH-01**: Update Windows paths in middleware_server.py - Phase 2 ✓
- [x] **PATH-02**: Update Windows paths in all scripts - Phase 2 ✓

### Memory Storage

- [x] **MEM-01**: Store facts as entity-predicate-value with metadata - Phase 3 ✓
- [x] **MEM-02**: Retrieve facts by entity, predicate, or scope - Phase 3 ✓

### API

- [x] **API-01**: Create API endpoint to serve facts - Phase 4 ✓
- [x] **API-02**: Dashboard fetches data from API - Phase 4 ✓

### Session Management

- [x] **SESS-01**: Open and close episodes (session contexts) - Phase 5 ✓
- [x] **SESS-02**: Retrieve facts scoped to active episode - Phase 5 ✓
- [x] **SESS-03**: Track episode purpose and active scopes - Phase 5 ✓

## v2 Requirements

Deferred to future release.

### Conflict Resolution

- **CONF-01**: Detect entity-predicate conflicts
- **CONF-02**: Resolve conflicts via temporal ordering (Wedderburn-Kasczinski)
- **CONF-03**: Track decisions for resolved conflicts

### Ring Theory

- **RING-01**: Implement graded ring decomposition
- **RING-02**: Implement ideal-theoretic forgetting
- **RING-03**: Support confidence-weighted facts (module scalars)

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
| DEP-01 | Phase 1 | ✓ Complete |
| DEP-02 | Phase 1 | ✓ Complete |
| PATH-01 | Phase 2 | ✓ Complete |
| PATH-02 | Phase 2 | ✓ Complete |
| MEM-01 | Phase 3 | ✓ Complete |
| MEM-02 | Phase 3 | ✓ Complete |
| API-01 | Phase 4 | ✓ Complete |
| API-02 | Phase 4 | ✓ Complete |
| SESS-01 | Phase 5 | ✓ Complete |
| SESS-02 | Phase 5 | ✓ Complete |
| SESS-03 | Phase 5 | ✓ Complete |

**Coverage:**

- v1 requirements: 17 total
- Mapped to phases: 17
- Unmapped: 0 ✓

---
*Requirements defined: 2026-06-18*
*Last updated: 2026-06-20 - All phases complete*
