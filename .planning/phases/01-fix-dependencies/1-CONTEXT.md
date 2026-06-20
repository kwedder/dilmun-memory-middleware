# Phase 1: Fix Dependencies - Context

**Gathered:** 2026-06-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix Python import paths and install missing dependencies. The middleware works but scripts fail due to Windows paths and missing modules.

</domain>

<decisions>
## Implementation Decisions

### Python path strategy

- **D-01:** Use absolute path `/home/kworqs/dilmun-memory-middleware` for sys.path.insert
- **D-02:** Import from `dilmun` package directly (from dilmun import DilmunMemoryMiddleware)

### Dependencies

- **D-03:** Install `python-dotenv` for environment variable loading
- **D-04:** Install `requests` for HTTP operations (shopify_auth.py)

### Vault location

- **D-05:** Use `/home/kworqs/.pi/subdilmun` as the vault path for all scripts

</decisions>

<specifics>
## Specific Ideas

- All scripts need to work in the Linux environment
- No need to maintain Windows compatibility

</specifics>

<canonical_refs>

## Canonical References

### Middleware code

- `dilmun-memory-middleware/dilmun/middleware.py` - Main middleware class
- `dilmun-memory-middleware/dilmun/__init__.py` - Package exports
- `dilmun-memory-middleware/dilmun/memory_store.py` - Storage layer

### Planning docs

- `.planning/PROJECT.md` - Project context and requirements
- `.planning/REQUIREMENTS.md` - Detailed requirements list
- `.planning/ROADMAP.md` - Phase breakdown

</canonical_refs>

<code_context>

## Existing Code Insights

### Reusable Assets

- `DilmunMemoryMiddleware` class: Main interface for memory operations
- `MemoryStore` class: File-based persistence layer
- `GradedMemoryRing`: Ring-theoretic memory operations

### Integration Points

- Scripts in `.pi/skills/dilmun-protocol/scripts/` need to import from middleware
- Vault at `/home/kworqs/.pi/subdilmun` is the data source

</code_context>

<deferred>
## Deferred Ideas

None - this phase is focused on fixing immediate blockers

</deferred>

---

*Phase: 01-fix-dependencies*
*Context gathered: 2026-06-19*
