"""
Benchmark: Dilmun (algebraic memory) vs ChromaDB (vector memory).

ChromaDB is a widely used vector store for agent/RAG memory; the same
top-k-by-similarity retrieval underlies Mem0 and LangChain's vector memory.
This benchmark runs ChromaDB's real HNSW index but supplies a deterministic,
offline embedding function (a hashing bag-of-words vectorizer) so the run
needs no model download and is fully reproducible.

The workload is the case that actually separates the two designs: facts about
entities where an attribute is *updated / contradicted over time*, then a
query for the CURRENT value. Later timestamp = ground truth.

    Dilmun     — canonicalize() resolves (entity, predicate) conflicts by
                 last-writer-wins, so the current value is returned by
                 construction.
    Chroma     — retrieves by embedding similarity. All versions of an
                 attribute share the same entity/predicate tokens, so a
                 query cannot tell the current value from a stale one unless
                 recency is added explicitly (metadata + arg-max timestamp),
                 which is essentially re-implementing canonicalize by hand.

Three retrievers are measured:
    dilmun          — memory.query(entity, predicate)
    chroma_top1     — nearest neighbour by similarity (naive vector memory)
    chroma_recency  — top-k by similarity, then newest timestamp (fair variant)

Reported: write throughput, mean query latency, and — the headline —
current-value accuracy.
"""

from __future__ import annotations

import hashlib
import random
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from dilmun import DilmunMemory

import chromadb

# --------------------------------------------------------------------------
# workload
# --------------------------------------------------------------------------

N_ENTITIES = 200
ATTRIBUTES = ["favorite_color", "home_city", "current_job"]
N_VERSIONS = 4          # how many times each attribute is overwritten
SEED = 7

VALUE_POOLS = {
    "favorite_color": ["blue", "red", "green", "amber", "violet", "teal"],
    "home_city": ["miami", "orlando", "tampa", "austin", "denver", "seattle"],
    "current_job": ["engineer", "teacher", "pilot", "chef", "nurse", "analyst"],
}


def build_workload() -> Tuple[List[dict], Dict[Tuple[str, str], str]]:
    """Return (facts_in_write_order, ground_truth_current_value).

    Each (entity, attribute) is written N_VERSIONS times with strictly
    increasing timestamps; the last write is the current truth.
    """
    rng = random.Random(SEED)
    facts: List[dict] = []
    writes = []
    for e in range(N_ENTITIES):
        entity = f"user_{e}"
        for attr in ATTRIBUTES:
            pool = VALUE_POOLS[attr]
            for _ in range(N_VERSIONS):
                writes.append((entity, attr, rng.choice(pool)))
    # interleave writes so no system can exploit write order, then assign
    # globally increasing timestamps in that shuffled order
    rng.shuffle(writes)
    t = 1000.0
    truth: Dict[Tuple[str, str], str] = {}
    for entity, attr, value in writes:
        facts.append({"entity": entity, "predicate": attr, "value": value, "t": t})
        # ground truth is the value carrying the highest timestamp (LWW)
        truth[(entity, attr)] = value
        t += 1.0
    return facts, truth


# --------------------------------------------------------------------------
# deterministic offline embedding (hashing bag-of-words)
# --------------------------------------------------------------------------

EMBED_DIM = 256


def embed(text: str) -> List[float]:
    vec = np.zeros(EMBED_DIM, dtype=np.float32)
    for tok in text.lower().replace("_", " ").split():
        h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
        vec[h % EMBED_DIM] += 1.0
    norm = np.linalg.norm(vec)
    if norm:
        vec /= norm
    return vec.tolist()


# --------------------------------------------------------------------------
# systems
# --------------------------------------------------------------------------

def run_dilmun(facts, truth):
    tmp = tempfile.mkdtemp()
    memory = DilmunMemory(tmp, backend="json")

    t0 = time.perf_counter()
    for f in facts:
        memory.write_fact(f["entity"], f["predicate"], f["value"], timestamp=f["t"])
    write_s = time.perf_counter() - t0

    correct = 0
    latencies = []
    for (entity, attr), current in truth.items():
        q0 = time.perf_counter()
        results = memory.query(entity=entity, predicate=attr)
        latencies.append(time.perf_counter() - q0)
        got = results[0].value if results else None
        if got == current:
            correct += 1
    memory.close()
    return {
        "name": "dilmun",
        "write_s": write_s,
        "accuracy": correct / len(truth),
        "mean_query_ms": 1000 * sum(latencies) / len(latencies),
    }


def run_chroma(facts, truth):
    client = chromadb.EphemeralClient()
    coll = client.create_collection(
        name="mem", metadata={"hnsw:space": "cosine"}
    )

    ids, embeddings, metadatas, documents = [], [], [], []
    for i, f in enumerate(facts):
        ids.append(str(i))
        documents.append(f"{f['entity']} {f['predicate']} {f['value']}")
        embeddings.append(embed(f"{f['entity']} {f['predicate']} {f['value']}"))
        metadatas.append({
            "entity": f["entity"], "predicate": f["predicate"],
            "value": f["value"], "t": f["t"],
        })

    t0 = time.perf_counter()
    # batch add (Chroma's native path); this is its write cost
    B = 1000
    for s in range(0, len(ids), B):
        coll.add(
            ids=ids[s:s + B], embeddings=embeddings[s:s + B],
            metadatas=metadatas[s:s + B], documents=documents[s:s + B],
        )
    write_s = time.perf_counter() - t0

    top1_correct = 0
    recency_correct = 0
    latencies = []
    for (entity, attr), current in truth.items():
        qemb = embed(f"{entity} {attr}")
        # (1) naive semantic memory: nearest neighbour by similarity
        q0 = time.perf_counter()
        res = coll.query(query_embeddings=[qemb], n_results=1)
        latencies.append(time.perf_counter() - q0)
        metas = res["metadatas"][0]
        if metas and metas[0]["value"] == current:
            top1_correct += 1

        # (2) recovery path: don't use the vector index at all — metadata
        # filter to (entity, predicate) then arg-max timestamp. This is
        # canonicalize (LWW) reimplemented on top of the store.
        got = coll.get(where={"$and": [
            {"entity": {"$eq": entity}},
            {"predicate": {"$eq": attr}},
        ]})
        cand = got["metadatas"]
        if cand:
            pick = max(cand, key=lambda m: m["t"])
            if pick["value"] == current:
                recency_correct += 1
    return {
        "name": "chroma",
        "write_s": write_s,
        "top1_accuracy": top1_correct / len(truth),
        "recency_accuracy": recency_correct / len(truth),
        "mean_query_ms": 1000 * sum(latencies) / len(latencies),
    }


# --------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------

def main():
    facts, truth = build_workload()
    n_writes = len(facts)
    n_queries = len(truth)
    print(f"workload: {N_ENTITIES} entities x {len(ATTRIBUTES)} attributes "
          f"x {N_VERSIONS} versions")
    print(f"          {n_writes} writes, {n_queries} current-value queries\n")

    d = run_dilmun(facts, truth)
    c = run_chroma(facts, truth)

    def wps(r):
        return n_writes / r["write_s"]

    print(f"{'metric':<26}{'Dilmun':>14}{'ChromaDB':>16}")
    print("-" * 56)
    print(f"{'write throughput (w/s)':<26}{wps(d):>14,.0f}{wps(c):>16,.0f}")
    print(f"{'mean query latency (ms)':<26}{d['mean_query_ms']:>14.3f}"
          f"{c['mean_query_ms']:>16.3f}")
    print(f"{'current-value accuracy':<26}{d['accuracy']:>13.1%}"
          f"{c['top1_accuracy']:>15.1%}  (vector top-1)")
    print(f"{'':<26}{'':>14}{c['recency_accuracy']:>15.1%}  (metadata + LWW)")
    print()
    print("notes:")
    print("  * Dilmun accuracy is exact by construction (canonicalize = LWW).")
    print("  * Chroma vector top-1 retrieves by similarity; stale and current")
    print("    versions are near-identical in embedding space, so similarity")
    print("    cannot tell which value is current -> ~chance accuracy.")
    print("  * Chroma 'metadata + LWW' ignores the vector index and does a")
    print("    metadata filter on (entity, predicate) + arg-max timestamp,")
    print("    i.e. re-implementing canonicalize -- at which point the vector")
    print("    store is just key-value storage.")
    print("  * Dilmun writes include disk persistence; Chroma runs in-memory.")


if __name__ == "__main__":
    main()
