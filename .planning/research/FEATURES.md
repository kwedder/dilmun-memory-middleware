# Feature Research

## Table Stakes (v1 Must-Have)

**Memory Storage:**

- Store entity-predicate-value facts with metadata
- Retrieve facts by entity, predicate, or scope
- Timestamp-based versioning

**Session Management:**

- Open/close episodes (session contexts)
- Scoped fact retrieval within episodes
- Automatic expiration of old facts

**Conflict Resolution:**

- Detect entity-predicate-value conflicts
- Wedderburn-Kasczinski temporal ordering
- Decision tracking for resolved conflicts

## Differentiators

**Ring-Theoretic Memory:**

- Graded ring decomposition by session
- Ideal-theoretic forgetting mechanism
- Module-valued confidence weighting
- Tensor product relationships between facts

**Memory Compression:**

- 3-strand recombination (assertion/provenance/dissent)
- Conservation invariant checking
- Cross-partition compression

## Anti-Features (Explicitly NOT Building)

- Real-time sync across devices
- Multi-agent shared memory
- Image/audio memory storage
- SQL/NoSQL database integration (file-based only)

---
*Research: Features dimension*
