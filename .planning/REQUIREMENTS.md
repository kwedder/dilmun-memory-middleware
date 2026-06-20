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
- [ ] **API-02**: Dashboard fetches data from API

### Session Management

- [ ] **SESS-01**: Open and close episodes (session contexts)
- [ ] **SESS-02**: Retrieve facts scoped to active episode
- [ ] **SESS-03**: Track episode purpose and active scopes

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
| API-02 | Phase 4 | Pending |
| SESS-01 | Phase 5 | Pending |
| SESS-02 | Phase 5 | Pending |
| SESS-03 | Phase 5 | Pending |

**Coverage:**

- v1 requirements: 17 total
- Mapped to phases: 17
- Unmapped: 0 ✓

---
*Requirements defined: 2026-06-18*
*Last updated: 2026-06-20 after Phase 4 progress*
