"""
Storage backends.

    JSONVault      — append-only JSON-lines vault on disk (default)
    SQLiteBackend  — single-file SQLite database

Both persist the same immutable facts and episode records; DilmunMemory
behaves identically on top of either. Facts are only rewritten when a
destructive operator (forget with apply=True) compacts the store.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

from .fact import Fact


class Backend:
    """Interface shared by all storage backends."""

    def append(self, fact: Fact) -> None:
        raise NotImplementedError

    def load(self) -> List[Fact]:
        raise NotImplementedError

    def replace_all(self, facts: List[Fact]) -> None:
        raise NotImplementedError

    def save_episodes(self, episodes: Dict[str, Dict]) -> None:
        raise NotImplementedError

    def load_episodes(self) -> Dict[str, Dict]:
        raise NotImplementedError

    def close(self) -> None:
        pass


class JSONVault(Backend):
    """Default backend: a vault directory holding

        facts.jsonl     — one immutable fact per line, append-only
        episodes.json   — episode open/close records
    """

    def __init__(self, vault_path: str = "./vault"):
        self.vault_path = Path(vault_path)
        self.vault_path.mkdir(parents=True, exist_ok=True)
        self.facts_file = self.vault_path / "facts.jsonl"
        self.episodes_file = self.vault_path / "episodes.json"

    def append(self, fact: Fact) -> None:
        with self.facts_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(fact.to_dict()) + "\n")

    def load(self) -> List[Fact]:
        if not self.facts_file.exists():
            return []
        facts = []
        with self.facts_file.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    facts.append(Fact.from_dict(json.loads(line)))
        return facts

    def replace_all(self, facts: List[Fact]) -> None:
        with self.facts_file.open("w", encoding="utf-8") as f:
            for fact in facts:
                f.write(json.dumps(fact.to_dict()) + "\n")

    def save_episodes(self, episodes: Dict[str, Dict]) -> None:
        self.episodes_file.write_text(
            json.dumps(episodes, indent=2), encoding="utf-8"
        )

    def load_episodes(self) -> Dict[str, Dict]:
        if not self.episodes_file.exists():
            return {}
        return json.loads(self.episodes_file.read_text(encoding="utf-8"))


class SQLiteBackend(Backend):
    """SQLite backend: everything in <vault_path>/dilmun.sqlite3."""

    def __init__(self, vault_path: str = "./vault"):
        self.vault_path = Path(vault_path)
        self.vault_path.mkdir(parents=True, exist_ok=True)
        self.db_path = self.vault_path / "dilmun.sqlite3"
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS facts (
                id TEXT PRIMARY KEY,
                entity TEXT NOT NULL,
                predicate TEXT NOT NULL,
                value TEXT NOT NULL,
                timestamp REAL NOT NULL,
                confidence REAL NOT NULL,
                episode TEXT,
                seq INTEGER NOT NULL,
                expires_at REAL,
                derived_from TEXT
            )"""
        )
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS episodes (
                id TEXT PRIMARY KEY,
                record TEXT NOT NULL
            )"""
        )
        self._conn.commit()

    def append(self, fact: Fact) -> None:
        d = fact.to_dict()
        self._conn.execute(
            "INSERT INTO facts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                d["id"], d["entity"], d["predicate"], json.dumps(d["value"]),
                d["timestamp"], d["confidence"], d["episode"], d["seq"],
                d["expires_at"],
                json.dumps(d["derived_from"]) if d["derived_from"] else None,
            ),
        )
        self._conn.commit()

    def load(self) -> List[Fact]:
        rows = self._conn.execute(
            "SELECT id, entity, predicate, value, timestamp, confidence, "
            "episode, seq, expires_at, derived_from FROM facts ORDER BY seq"
        ).fetchall()
        return [
            Fact.from_dict({
                "id": r[0], "entity": r[1], "predicate": r[2],
                "value": json.loads(r[3]), "timestamp": r[4],
                "confidence": r[5], "episode": r[6], "seq": r[7],
                "expires_at": r[8],
                "derived_from": json.loads(r[9]) if r[9] else None,
            })
            for r in rows
        ]

    def replace_all(self, facts: List[Fact]) -> None:
        self._conn.execute("DELETE FROM facts")
        self._conn.commit()
        for fact in facts:
            self.append(fact)

    def save_episodes(self, episodes: Dict[str, Dict]) -> None:
        self._conn.execute("DELETE FROM episodes")
        for episode_id, record in episodes.items():
            self._conn.execute(
                "INSERT INTO episodes VALUES (?, ?)",
                (episode_id, json.dumps(record)),
            )
        self._conn.commit()

    def load_episodes(self) -> Dict[str, Dict]:
        rows = self._conn.execute("SELECT id, record FROM episodes").fetchall()
        return {r[0]: json.loads(r[1]) for r in rows}

    def close(self) -> None:
        self._conn.close()


BACKENDS = {
    "json": JSONVault,
    "sqlite": SQLiteBackend,
}


def make_backend(name: str, vault_path: str) -> Backend:
    try:
        return BACKENDS[name](vault_path)
    except KeyError:
        raise ValueError(
            f"unknown backend {name!r}; available: {sorted(BACKENDS)}"
        ) from None
