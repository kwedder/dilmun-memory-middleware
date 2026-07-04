# Dilmun Memory Middleware

*A deterministic, algebraically structured memory system for persistent AI agents.*

---

## Overview

Dilmun Memory Middleware is a persistent memory layer designed for AI systems that must operate across long time horizons, multiple sessions, and evolving knowledge states.

Instead of treating memory as:

* raw text logs, or
* embedding-based retrieval

Dilmun models memory as a **structured algebraic system of immutable facts**, governed by deterministic operations for:

* merging
* conflict resolution
* forgetting
* composition
* retrieval

---

# Core Idea

Memory is not a database.

Memory is a **structured algebraic object**.

We define a memory state:

[
M = {f_1, f_2, ..., f_n}
]

where each fact is:

[
f = (e, p, v, t, \nu)
]

* **e**: entity
* **p**: predicate
* **v**: value
* **t**: timestamp
* **ν(f)**: confidence valuation in ([0,1])

---

# Design Principles

* Facts are **immutable**
* Updates create **new facts**, not mutations
* Conflicts are resolved deterministically
* Memory transformations are idempotent
* Stale knowledge is removed via formal operators
* Retrieval is structured, not probabilistic guessing

---

# Installation

```bash
pip install dilmun
```

---

# Quick Start

```python
from dilmun import DilmunMemory

memory = DilmunMemory("./vault")

memory.open_episode("chat_001")

memory.write_fact(
    entity="user",
    predicate="favorite_color",
    value="blue",
    confidence=0.95
)

memory.write_fact(
    entity="user",
    predicate="location",
    value="Miami"
)

context = memory.get_context()

memory.close_episode()
```

---

# Algebraic Structure of Memory

## 1. Memory State Space

The memory system is a finite set:

[
M = {f_1, f_2, ..., f_n}
]

Each fact belongs to a structured state space.

---

## 2. Valuation Function (Confidence)

We define a valuation:

[
\nu : M \rightarrow [0,1]
]

This assigns reliability to each fact.

Properties:

* Higher values = stronger evidence
* Used for ranking and conflict resolution
* Composable across updates

---

## 3. Episode Partitioning (Graded Structure)

Memory is partitioned into **episodes**:

[
M = M_0 \cup M_1 \cup \dots \cup M_k
]

* (M_0): global memory
* (M_i): episode memory

This induces a **graded structure over time**, where:

* facts are isolated by context
* cross-episode promotion is explicit
* contamination is prevented by default

---

## 4. Canonicalization Operator

Conflicts occur when two facts share:

* entity
* predicate
* differing values

Example:

```
(user, city, Miami)
(user, city, Orlando)
```

We define a canonicalization operator:

[
C : M \rightarrow M
]

Selection rule:

1. Highest timestamp
2. Highest confidence
3. Stable insertion order (tie-breaker)

### Canonical Memory Property

* **Idempotence**
  [
  C(C(M)) = C(M)
  ]

* **Determinism**
  [
  M_1 = M_2 \Rightarrow C(M_1) = C(M_2)
  ]

---

## 5. Forgetting Operator (Closure System)

Instead of deletion, Dilmun uses a transformation:

[
F : M \rightarrow M
]

A fact is removed if it satisfies:

* expired timestamp
* low confidence
* contradiction pressure (optional policy)

### Properties

* **Idempotence**
  [
  F(F(M)) = F(M)
  ]

* **Monotonic reduction of stale information**

This defines a **closure system over memory space**.

---

## 6. Memory Graph Structure

Facts induce a directed labeled graph:

```
Alice ──likes──> Coffee
Coffee ──served_at──> Cafe
```

Formally:

* nodes = entities
* edges = predicates
* values = labeled relations

Retrieval becomes graph traversal instead of text search.

---

## 7. Composition of Facts (Relational Product)

Instead of tensor products, Dilmun uses **relational composition**.

Given:

```
(A, likes, B)
(B, category, C)
```

We derive:

```
(A, likes_category, C)
```

Defined as:

[
comp(f_1, f_2)
]

where composition is valid when:

[
f_1.v = f_2.e
]

This is a **path composition operator over the memory graph**.

---

## 8. Retrieval Function

Context retrieval is a scoring function:

[
score(f) = w_1 \nu(f) + w_2 \cdot recency + w_3 \cdot graph_centrality
]

Returned facts are:

[
\arg\max_M score(f)
]

This replaces embedding similarity with structured scoring.

---

# Core API

```python
memory.open_episode(id)

memory.write_fact(
    entity,
    predicate,
    value,
    confidence=1.0
)

memory.get_context()

memory.close_episode()
```

---

# Storage Backends

* JSON vault (default)
* SQLite backend
* Planned: PostgreSQL / DuckDB
* Planned: distributed CRDT memory

---

# Applications

* Long-horizon AI agents
* Robotics memory systems
* IoT device cognition layers
* Multi-agent coordination
* Persistent research assistants
* Workflow automation systems

---

# Formal Properties

Dilmun operations are designed to satisfy:

### Canonicalization

* idempotent
* deterministic
* conflict-resolving

### Forgetting

* idempotent closure operator
* stable under repeated application

### Episode structure

* partitioned memory space
* non-interfering updates by default

### Composition

* graph-consistent relational inference
* path-based derivation

---

# Roadmap

* Distributed memory synchronization (CRDT-based)
* Provenance tracking per fact
* Typed predicate system
* Temporal decay functions
* Query planner over memory graphs
* Optional probabilistic inference layer
* Formal verification of canonicalization + forgetting operators

---

# Philosophy

Dilmun is not an embedding database or a chatbot plugin.

It is a **deterministic memory algebra** for systems that must remember, reconcile, and evolve knowledge over time.

---

## License

MIT
