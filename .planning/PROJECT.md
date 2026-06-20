# Dilmun Memory Middleware

## What This Is

A Python library for AI agents to maintain persistent, structured memory that transcends context windows. Uses ring-theoretic mathematics (Wedderburn-Kasczinski) for automatic conflict resolution and forgetting.

## Core Value

**AI agents with persistent, structured memory that transcends context windows.**

Everything else can fail; this must work. This is the fundamental capability that enables AI agents to learn, adapt, and maintain coherent identity across sessions.

## Requirements

### Validated

(None yet - ship to validate)

### Active

- [ ] **MEM-01**: Store and retrieve facts with entity-predicate-value structure
- [ ] **MEM-02**: Support session-scoped memory with automatic expiration
- [ ] **MEM-03**: Implement ring-theoretic conflict resolution (Wedderburn-Kasczinski)
- [ ] **MEM-04**: Provide confidence-weighted fact retrieval
- [ ] **MEM-05**: Enable cross-skill event coordination via pub/sub
- [ ] **MEM-06**: Support memory compression (3-strand: assertion/provenance/dissent)
- [ ] **MEM-07**: Provide vector similarity search for facts
- [ ] **MEM-08**: Handle memory consolidation and forgetting

### Out of Scope

- [ ] Real-time collaborative memory - Too complex for v1
- [ ] Multi-modal memory (images, audio) - Text-first approach
- [ ] Distributed memory across multiple agents - Single-agent focus initially

## Context

The Dilmun Protocol is already deployed and working:

- 3,478 facts stored in production
- Integrated with Shopify, Goon Plates, and other skills
- GPMA/PandaSoulEngine consciousness model exists
- Memory compression (3-strand) is implemented separately

This extraction packages the proven middleware patterns into a reusable library.

**Current Issues Found:**

- Windows paths hardcoded in `middleware_server.py`, `write_project.py`, `check_index.py`, `active_check.py`, `shopify_auth.py`
- Import paths need updating to use `dilmun-memory-middleware` package
- Dashboard is a client-side demo, needs backend API connection

## Constraints

- **Tech stack**: Python 3.10+, no heavy ML dependencies
- **Storage**: File-based JSON (Obsidian vault compatible)
- **Performance**: Sub-second operations for common cases
- **Dependencies**: Minimal (just hashlib, json, pathlib)

## Key Decisions

| Decision | Rationale | Outcome |
| -------- | --------- | ------- |
| Ring-theoretic foundation | Novel approach to conflict resolution | ✓ Pending |
| Session grading | Natural expiration via graded components | ✓ Pending |
| Confidence weighting | Module-valued facts for reliability | ✓ Pending |

---
*Last updated: 2026-06-18 after initialization*
