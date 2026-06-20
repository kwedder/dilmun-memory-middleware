# Dilmun Memory Middleware

## What This Is

A Python library for AI agents to maintain persistent, structured memory that transcends context windows. Uses ring-theoretic mathematics (Wedderburn-Kasczinski) for automatic conflict resolution and forgetting.

## Core Value

**AI agents with persistent, structured memory that transcends context windows.**

Everything else can fail; this must work. This is the fundamental capability that enables AI agents to learn, adapt, and maintain coherent identity across sessions.

## Requirements

### Validated

- ✓ **MEM-01**: Store facts with entity-predicate-value structure - Working
- ✓ **MEM-02**: Retrieve facts by entity, predicate, or scope - Working
- ✓ **SESS-01**: Open/close episodes (session contexts) - Working
- ✓ **SESS-02**: Retrieve facts scoped to active episode - Working
- ✓ **SESS-03**: Track episode purpose and active scopes - Working

### Active

(None - v1 complete)

### Out of Scope

- [ ] Real-time collaborative memory - Too complex for v1
- [ ] Multi-modal memory (images, audio) - Text-first approach
- [ ] Distributed memory across multiple agents - Single-agent focus initially

## Context

The Dilmun Protocol is already deployed and working:

- 3,488+ facts stored in production
- Integrated with Shopify, Goon Plates, and other skills
- GPMA/PandaSoulEngine consciousness model exists
- Memory compression (3-strand) is implemented separately

This extraction packages the proven middleware patterns into a reusable library.

**Status:** All v1 requirements complete ✓

## Constraints

- **Tech stack**: Python 3.10+, no heavy ML dependencies
- **Storage**: File-based JSON (Obsidian vault compatible)
- **Performance**: Sub-second operations for common cases
- **Dependencies**: Minimal (just hashlib, json, pathlib)

## Key Decisions

| Decision | Rationale | Outcome |
| -------- | --------- | ------- |
| Ring-theoretic foundation | Novel approach to conflict resolution | ✓ Implemented |
| Session grading | Natural expiration via graded components | ✓ Implemented |
| Confidence weighting | Module-valued facts for reliability | ✓ Implemented |
| File-based storage | Obsidian vault compatibility | ✓ Verified |

---
*Last updated: 2026-06-20 - v1 complete*
