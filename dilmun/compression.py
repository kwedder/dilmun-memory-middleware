"""
Memory Compression - 3-strand recombination pipeline.

Strand A — assertion: what is believed true after the merge
Strand B — provenance: ordered list of source note paths  
Strand C — dissent:    source claims that didn't fit, with origin pointer

Conservation invariant is per-partition and checkable:
every source claim must be reachable from assertion ∪ dissent.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict

from .memory_store import MemoryStore


COMPRESSIBLE = {"fact", "tool", "skill-trace", "dialog"}
REFUSED = {"decision"}


class CompressionError(Exception):
    """Raised when compression cannot proceed."""
    pass


def extract_front_matter(content: str) -> Dict:
    """Extract JSON front-matter from content."""
    if not content.startswith("---"):
        return {}
    end = content.find("---", 3)
    if end == -1:
        return {}
    try:
        return json.loads(content[3:end].strip())
    except json.JSONDecodeError:
        return {}


def body_of(content: str) -> str:
    """Return the markdown body after the front-matter fence."""
    if not content.startswith("---"):
        return content
    end = content.find("---", 3)
    if end == -1:
        return content
    return content[end + 3:].lstrip("\n")


def compress_notes(store: MemoryStore, note_refs: List[str], partition: str,
                   threshold: float = 1.0, dry_run: bool = False) -> Dict:
    """
    Compress a set of source notes from `partition` into a single 3-strand note.
    """
    if partition in REFUSED:
        raise CompressionError(f"refusing to compress {partition}/: this partition is the audit trail")
    if partition not in COMPRESSIBLE:
        raise CompressionError(f"unknown partition: {partition}")
    if len(note_refs) < 2:
        raise CompressionError("need at least 2 source notes to compress")
    
    # Load notes
    notes = []
    for ref in note_refs:
        path = store.vault_path / partition / ref
        if not path.exists():
            raise CompressionError(f"source note not found: {ref}")
        content = path.read_text(encoding="utf-8")
        meta = extract_front_matter(content)
        if meta.get("compressed_into"):
            raise CompressionError(f"source already compressed: {path}")
        notes.append({
            "path": str(path),
            "content": content,
            "metadata": meta,
            "body": body_of(content).strip(),
        })
    
    # Compress based on partition type
    if partition == "fact":
        assertion, dissent, covered, total, unit = _compress_fact(notes)
    elif partition in ("tool", "skill-trace"):
        assertion, dissent, covered, total, unit = _compress_tool_like(notes, partition)
    elif partition == "dialog":
        assertion, dissent, covered, total, unit = _compress_dialog(notes)
    else:
        raise CompressionError(f"no compressor for partition: {partition}")
    
    ratio = covered / total if total > 0 else 0
    if ratio < threshold:
        raise CompressionError(f"conservation failure: {covered}/{total} {unit} covered")
    
    result = {
        "compressed_note": None,
        "source_count": len(notes),
        "assertion_count": len(assertion),
        "dissent_count": len(dissent),
        "conservation_ratio": ratio,
        "unit": unit,
    }
    
    if dry_run:
        result["dry_run"] = True
        return result
    
    # Write compressed note
    note_id = uuid.uuid4().hex[:12]
    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    filename = f"compressed_{timestamp}_{note_id}.md"
    out_dir = store.vault_path / "compressed" / partition
    out_dir.mkdir(parents=True, exist_ok=True)
    filepath = out_dir / filename
    
    front_matter = {
        "id": note_id,
        "type": "compressed",
        "source_partition": partition,
        "created": datetime.now().isoformat(),
        "source_notes": [n["path"] for n in notes],
    }
    
    body = "\n".join([
        "## Strand A — Assertion",
        json.dumps(assertion, indent=2),
        "",
        "## Strand B — Provenance",
        json.dumps([n["path"] for n in notes], indent=2),
        "",
        "## Strand C — Dissent",
        json.dumps(dissent, indent=2) if dissent else "(none)",
    ]) + "\n"
    
    with filepath.open("w", encoding="utf-8") as f:
        f.write("---\n")
        f.write(json.dumps(front_matter, indent=2))
        f.write("\n---\n\n")
        f.write(body)
    
    result["compressed_note"] = str(filepath)
    return result


def _compress_fact(notes: List[Dict]) -> tuple:
    """Compress fact partition."""
    triples = []
    for n in notes:
        meta = n["metadata"].get("metadata", {})
        e, p, v = meta.get("entity"), meta.get("predicate"), meta.get("value")
        if e and p and v is not None:
            triples.append((e, p, v, n["path"]))
    
    by_key = defaultdict(list)
    for e, p, v, src in triples:
        by_key[(e, p)].append((v, src))
    
    assertion, dissent = [], []
    for (e, p), entries in by_key.items():
        counts = defaultdict(list)
        for v, src in entries:
            counts[v].append(src)
        if len(counts) == 1:
            v = next(iter(counts))
            assertion.append({"entity": e, "predicate": p, "value": v, "sources": sorted(counts[v])})
        else:
            ranked = sorted(counts.items(), key=lambda kv: (-len(kv[1]), max(kv[1])))
            winner_v, winner_srcs = ranked[0]
            assertion.append({"entity": e, "predicate": p, "value": winner_v, "sources": sorted(winner_srcs)})
            for v, srcs in ranked[1:]:
                for src in sorted(srcs):
                    dissent.append({"entity": e, "predicate": p, "value": v, "source": src})
    
    covered = sum(len(a["sources"]) for a in assertion) + len(dissent)
    return assertion, dissent, covered, len(triples), "triples"


def _compress_tool_like(notes: List[Dict], partition: str) -> tuple:
    """Compress tool/skill-trace partitions."""
    def created_of(n):
        return n["metadata"].get("created", "")
    notes_sorted = sorted(notes, key=created_of)
    
    by_key = defaultdict(list)
    nondet = []
    for n in notes_sorted:
        meta = n["metadata"]
        cmd = meta.get("metadata", {}).get("command") or meta.get("metadata", {}).get("skill_name") or ""
        env_hash = meta.get("environment_hash", "")
        output = n["body"]
        if not meta.get("deterministic", False):
            nondet.append((cmd, env_hash, output, n["path"]))
            continue
        by_key[(cmd, env_hash)].append((n, output))
    
    assertion, dissent = [], []
    for (cmd, env_hash), entries in by_key.items():
        latest_note, latest_output = entries[-1]
        assertion.append({"command": cmd, "environment_hash": env_hash, "output": latest_output, "source": latest_note["path"]})
        for n, out in entries[:-1]:
            if out != latest_output:
                dissent.append({"command": cmd, "environment_hash": env_hash, "output": out, "source": n["path"]})
    
    for cmd, env_hash, out, src in nondet:
        dissent.append({"command": cmd, "environment_hash": env_hash, "output": out, "source": src, "reason": "non-deterministic"})
    
    covered = sum(1 for a in assertion for _ in [a["source"]]) + len(dissent)
    return assertion, dissent, covered, len(notes), "notes"


def _compress_dialog(notes: List[Dict]) -> tuple:
    """Compress dialog partition."""
    line_to_sources = defaultdict(list)
    total_lines = 0
    for n in notes:
        for line in n["body"].splitlines():
            line = line.strip()
            if not line:
                continue
            total_lines += 1
            line_to_sources[line].append(n["path"])
    
    assertion, dissent = [], []
    for line, srcs in line_to_sources.items():
        if len(srcs) > 1:
            assertion.append({"line": line, "sources": sorted(set(srcs)), "count": len(srcs)})
        else:
            dissent.append({"line": line, "source": srcs[0]})
    
    covered = sum(a["count"] for a in assertion) + len(dissent)
    return assertion, dissent, covered, total_lines, "lines"