# Roadmap: Dilmun Memory Middleware

**5 phases** | **17 requirements** | All v1 requirements covered ✓

| #   | Phase           | Goal                           | Requirements    | Success Criteria |
| --- | --------------- | ------------------------------ | --------------- | ---------------- |
| 1   | Fix Dependencies | Resolve Python path/import issues | DEP-01, DEP-02  | Scripts run without errors |
| 2   | Fix Paths        | Update Windows paths to Linux | PATH-01, PATH-02 | All paths work on Linux |
| 3   | Memory Storage  | Persistent fact storage        | MEM-01, MEM-02  | CRUD operations work |
| 4   | Backend API      | Connect dashboard to middleware  | API-01, API-02  | Dashboard reads real data |
| 5   | Session Mgmt    | Episode contexts               | MEM-03, SESS-01, SESS-02, SESS-03 | Episodes scope memory |

## Phase Details

**Phase 1: Fix Dependencies**
Goal: Resolve Python path and import issues
Requirements: DEP-01, DEP-02
Success criteria:

1. All scripts import from correct package location
2. Scripts run without ModuleNotFoundError

**Phase 2: Fix Paths**
Goal: Update all Windows paths to Linux-compatible paths
Requirements: PATH-01, PATH-02
Success criteria:

1. middleware_server.py uses Linux paths
2. All scripts reference correct vault location

**Phase 3: Memory Storage**
Goal: Basic fact storage and retrieval
Requirements: MEM-01, MEM-02
Success criteria:

1. Write facts with entity-predicate-value structure
2. Read facts by entity, predicate, or scope
3. All operations complete in <100ms

**Phase 4: Backend API**
Goal: Connect dashboard to Python middleware
Requirements: API-01, API-02
Success criteria:

1. API endpoint serves facts from middleware
2. Dashboard fetches real data from /home/kworqs/.pi/subdilmun

**Phase 5: Session Management**
Goal: Episode-scoped memory with TTL
Requirements: MEM-03, SESS-01, SESS-02, SESS-03
Success criteria:

1. Open/close episodes
2. Scoped fact retrieval
3. Automatic expiration of stale facts

---
*Roadmap updated: 2026-06-19 after diagnosing issues*
