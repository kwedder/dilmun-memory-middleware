"""
bench_nabu — a "scribe of the world" benchmark for fact-acquisition agents.

Named for Nabu, the Babylonian god of scribes and record-keeping: the task is
to amass VERIFIED facts across three domains that triangulate human physical
experience — the body (emergency medicine), matter (chemistry), and culture
(anthropology) — and be scored on whether what was written is actually true.

Design (matches the repo's dilmun-vs-baseline benches):

  * A small, versioned seed manifest (nabu_seed.json) lists target entities,
    their required predicates, and authoritative values. All three domains use
    open, structured sources so every write is checkable — no LLM grades an LLM.

  * TWO reference modes, like results.json's dilmun-vs-vector pairs:
      --baseline  a deterministic, no-LLM harvester fills the manifest directly.
                  It is the floor an agent must beat AND it writes the
                  ground-truth snapshot to disk for fully-offline scoring.
      --agent S   score a Dilmun store S (JSON list of fact dicts, i.e.
                  Fact.to_dict()) produced by a real Pi mission, against the
                  snapshot — through the real canonicalize()/derive() operators.

  * --refresh     hit the live APIs (PubChem PUG REST, openFDA) and report
                  agreement with the hand-curated seed (verify-then-trust).

Efficiency thesis: harvest STRUCTURED sources first (facts arrive pre-shaped as
triples), and let composition grow the reading list — every fact whose value is
a new entity becomes the next mission target. The frontier is the curriculum.

Metrics (all deterministic):
    coverage              filled (entity,predicate) / manifest
    veridicality          strict facts whose value matches the authority
    confabulation_rate    canonical writes on known keys with a WRONG value
    off_schema_rate       canonical writes on entities/predicates not in schema
    duplicate_suppression canonical facts / raw writes  (is C earning its keep)
    cross_domain_yield    derived facts (via ∘) whose parents span two domains
    efficiency            canonical facts per 1k tokens (agent) or facts/sec
    temporal_grounding    session t_end - t_start vs wall clock (the timer thesis)

Usage:
    py benchmarks/nabu/bench_nabu.py --baseline
    py benchmarks/nabu/bench_nabu.py --baseline --refresh
    py benchmarks/nabu/bench_nabu.py --agent path/to/store.json --tokens 42000
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent))
from dilmun import Fact, canonicalize, composable, derive  # real operators


# ─────────────────────────────────────────────────────────────────────────
# seed / manifest
# ─────────────────────────────────────────────────────────────────────────
def load_seed() -> dict:
    return json.loads((HERE / "nabu_seed.json").read_text(encoding="utf-8"))


def manifest_keys(seed: dict):
    """Every (entity, predicate) the agent is asked to learn."""
    for ent, spec in seed["entities"].items():
        for pred in spec["facts"]:
            yield ent, pred


def domain_of(seed: dict, entity: str) -> str:
    spec = seed["entities"].get(entity)
    return spec["domain"] if spec else "unknown"


def norm(v) -> str:
    return str(v).strip().lower()


def value_matches(store_v, gt) -> bool:
    """gt is {'v': value, optional 'tol': float}. Numeric tol or exact-ci."""
    if "tol" in gt:
        try:
            return abs(float(store_v) - float(gt["v"])) <= gt["tol"]
        except (TypeError, ValueError):
            return False
    return norm(store_v) == norm(gt["v"])


# ─────────────────────────────────────────────────────────────────────────
# live sources (stdlib only; best-effort, guarded)  — verify-then-trust
# ─────────────────────────────────────────────────────────────────────────
def _get_json(url: str, timeout: float = 8.0):
    req = urllib.request.Request(url, headers={"User-Agent": "bench_nabu/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def pubchem(name: str) -> dict:
    """PubChem PUG REST — authoritative, public domain. formula + MW + CID."""
    base = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/"
    props = _get_json(base + urllib.parse.quote(name) +
                      "/property/MolecularFormula,MolecularWeight/JSON")
    p = props["PropertyTable"]["Properties"][0]
    return {"molecular_formula": p["MolecularFormula"],
            "molecular_weight": float(p["MolecularWeight"]),
            "cid": str(p["CID"])}


def openfda(name: str) -> dict:
    """openFDA drug label — US-approved usage. Best-effort indication text."""
    url = ("https://api.fda.gov/drug/label.json?search=openfda.generic_name:"
           + urllib.parse.quote(name) + "&limit=1")
    d = _get_json(url)
    res = d["results"][0]
    return {"indication_text": (res.get("indications_and_usage") or [""])[0][:200]}


def refresh_report(seed: dict) -> dict:
    """Cross-check hand-curated chem values against live PubChem."""
    agree = disagree = errors = 0
    notes = []
    for ent, spec in seed["entities"].items():
        if spec["domain"] != "chem":
            continue
        try:
            live = pubchem(ent)
        except Exception as e:  # network / name miss — don't fail the bench
            errors += 1
            notes.append(f"  {ent}: fetch error ({type(e).__name__})")
            continue
        for pred in ("molecular_formula", "molecular_weight"):
            gt = spec["facts"].get(pred)
            if not gt:
                continue
            if value_matches(live[pred], gt):
                agree += 1
            else:
                disagree += 1
                notes.append(f"  {ent}.{pred}: seed={gt['v']} live={live[pred]}")
    return {"agree": agree, "disagree": disagree, "errors": errors, "notes": notes}


# ─────────────────────────────────────────────────────────────────────────
# baseline harvester — deterministic, no LLM. also writes the snapshot.
# ─────────────────────────────────────────────────────────────────────────
def baseline_store(seed: dict, now: float) -> list[Fact]:
    """Fill the manifest directly from the seed. This is the floor and the
    ground-truth snapshot: coverage 1.0, veridicality 1.0 by construction."""
    facts, seq = [], 0
    for ent, spec in seed["entities"].items():
        for pred, gt in spec["facts"].items():
            facts.append(Fact(entity=ent, predicate=pred, value=gt["v"],
                              timestamp=now, confidence=1.0, seq=seq))
            seq += 1
    return facts


def snapshot(seed: dict, path: Path):
    path.write_text(json.dumps(seed, indent=2, ensure_ascii=False), encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────
# scorer — runs the REAL operators over whatever store it's given
# ─────────────────────────────────────────────────────────────────────────
def score(seed: dict, raw_facts: list[Fact], *, tokens: int | None,
          wall_seconds: float | None) -> dict:
    keys = set(manifest_keys(seed))
    ent_specs = seed["entities"]

    raw_n = len(raw_facts)
    canon = canonicalize(raw_facts)            # ← the real C operator
    canon_by_key = {(f.entity, f.predicate): f for f in canon}

    # coverage
    covered = sum(1 for k in keys if k in canon_by_key)
    coverage = covered / len(keys) if keys else 0.0

    # veridicality (strict facts only) + confabulation on known keys
    strict_total = strict_true = 0
    confab = 0
    for ent, pred in keys:
        gt = ent_specs[ent]["facts"][pred]
        strict = gt.get("strict", True)
        f = canon_by_key.get((ent, pred))
        if strict:
            strict_total += 1
            if f and value_matches(f.value, gt):
                strict_true += 1
        if f and not value_matches(f.value, gt):
            confab += 1                        # wrote a known key with a wrong value
    veridicality = strict_true / strict_total if strict_total else 0.0

    # off-schema writes: canonical facts on entities/predicates the manifest never asked for
    off_schema = sum(1 for f in canon
                     if (f.entity, f.predicate) not in keys)
    known_key_writes = sum(1 for f in canon if (f.entity, f.predicate) in keys)
    confab_rate = confab / known_key_writes if known_key_writes else 0.0
    off_schema_rate = off_schema / len(canon) if canon else 0.0

    # duplicate suppression — did C actually collapse re-ingests?
    dup_suppression = len(canon) / raw_n if raw_n else 1.0

    # cross-domain compose yield — derive() is the real ∘ operator
    derived = derive(canon)
    cross = []
    for d in derived:
        if not d.derived_from:
            continue
        p1 = next((f for f in canon if f.id == d.derived_from[0]), None)
        p2 = next((f for f in canon if f.id == d.derived_from[1]), None)
        if p1 and p2 and domain_of(seed, p1.entity) != domain_of(seed, p2.entity):
            cross.append((p1.entity, p2.entity, d.predicate, d.value))

    # efficiency
    if tokens:
        efficiency = {"canonical_facts_per_1k_tokens": round(len(canon) / (tokens / 1000), 2),
                      "tokens": tokens}
    elif wall_seconds:
        efficiency = {"canonical_facts_per_sec": round(len(canon) / wall_seconds, 1),
                      "wall_seconds": round(wall_seconds, 3)}
    else:
        efficiency = {"note": "pass --tokens (agent) for the amassing-efficiency number"}

    # temporal grounding — the timer thesis: duration is a fact-difference
    temporal = temporal_grounding(raw_facts)

    return {
        "manifest_keys": len(keys),
        "raw_writes": raw_n,
        "canonical_facts": len(canon),
        "coverage": round(coverage, 4),
        "veridicality": round(veridicality, 4),
        "confabulation_rate": round(confab_rate, 4),
        "off_schema_rate": round(off_schema_rate, 4),
        "duplicate_suppression": round(dup_suppression, 4),
        "cross_domain_yield": len(cross),
        "cross_domain_examples": [f"{a} ∘ {b} ⇒ {p} = {v}" for a, b, p, v in cross[:6]],
        "efficiency": efficiency,
        "temporal_grounding": temporal,
    }


def temporal_grounding(facts: list[Fact]) -> dict:
    """If the store carries a mission timer (session.timer_start/timer_stop),
    report elapsed as t_stop - t_start — computed, never estimated."""
    starts = [f for f in facts if f.predicate in ("timer_start", "session_start")]
    stops = [f for f in facts if f.predicate in ("timer_stop", "session_end")]
    if not starts or not stops:
        return {"present": False,
                "note": "no timer facts; a mission that writes timer_start/stop gets a scored duration"}
    t0 = min(float(f.value) if _isnum(f.value) else f.timestamp for f in starts)
    t1 = max(float(f.value) if _isnum(f.value) else f.timestamp for f in stops)
    return {"present": True, "elapsed_seconds": round(t1 - t0, 3),
            "basis": "t_stop - t_start (fact-difference)"}


def _isnum(v) -> bool:
    try:
        float(v); return True
    except (TypeError, ValueError):
        return False


# ─────────────────────────────────────────────────────────────────────────
# agent-store loading
# ─────────────────────────────────────────────────────────────────────────
def load_store(path: Path) -> list[Fact]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data["facts"] if isinstance(data, dict) and "facts" in data else data
    facts, seq = [], 0
    for r in rows:
        facts.append(Fact(
            entity=str(r["entity"]), predicate=str(r["predicate"]), value=r["value"],
            timestamp=float(r.get("timestamp", 0.0)),
            confidence=float(r.get("confidence", 1.0)),
            seq=int(r.get("seq", seq)),
        ))
        seq += 1
    return facts


# ─────────────────────────────────────────────────────────────────────────
# report
# ─────────────────────────────────────────────────────────────────────────
def pct(x):
    return f"{x:.1%}" if isinstance(x, float) and 0 <= x <= 1 else str(x)


def print_report(title: str, seed: dict, res: dict):
    print(f"\n{title}")
    print("─" * 62)
    order = ["coverage", "veridicality", "confabulation_rate", "off_schema_rate",
             "duplicate_suppression", "cross_domain_yield"]
    for k in order:
        print(f"  {k:<24}{pct(res[k]) if isinstance(res[k], float) else res[k]}")
    print(f"  {'canonical / raw':<24}{res['canonical_facts']} / {res['raw_writes']}  "
          f"({res['manifest_keys']} manifest keys)")
    if res["cross_domain_examples"]:
        print("  cross-domain (∘):")
        for ex in res["cross_domain_examples"]:
            print(f"      {ex}")
    print(f"  efficiency               {res['efficiency']}")
    tg = res["temporal_grounding"]
    print(f"  temporal grounding       {'elapsed ' + str(tg['elapsed_seconds']) + 's' if tg.get('present') else tg['note']}")


def main():
    try:  # box-drawing / ∘ glyphs on any console (Windows cp1252 etc.)
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="bench_nabu — verified fact-acquisition benchmark")
    ap.add_argument("--baseline", action="store_true", help="run deterministic harvester + write snapshot")
    ap.add_argument("--agent", metavar="STORE.json", help="score a Dilmun store from a Pi mission")
    ap.add_argument("--tokens", type=int, default=None, help="agent token spend, for efficiency")
    ap.add_argument("--refresh", action="store_true", help="cross-check chem seed against live PubChem")
    args = ap.parse_args()

    seed = load_seed()
    if not (args.baseline or args.agent or args.refresh):
        args.baseline = True  # sensible default

    print("bench_nabu — scribe-of-the-world · body · matter · culture")
    for dom, note in seed["meta"]["honesty"].items():
        print(f"  [{dom}] {note}")

    if args.refresh:
        rep = refresh_report(seed)
        print(f"\nlive PubChem cross-check: {rep['agree']} agree · "
              f"{rep['disagree']} disagree · {rep['errors']} errors")
        for n in rep["notes"]:
            print(n)

    if args.baseline:
        t0 = time.perf_counter()
        store = baseline_store(seed, now=time.time())
        wall = time.perf_counter() - t0
        snap = HERE / "ground_truth.json"
        snapshot(seed, snap)
        res = score(seed, store, tokens=None, wall_seconds=wall or 1e-6)
        print_report("BASELINE (deterministic harvester — the floor)", seed, res)
        print(f"\nwrote snapshot → {snap}")
        (HERE / "nabu_results.json").write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")

    if args.agent:
        store = load_store(Path(args.agent))
        res = score(seed, store, tokens=args.tokens, wall_seconds=None)
        print_report(f"AGENT ({args.agent})", seed, res)
        (HERE / "nabu_agent_results.json").write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
