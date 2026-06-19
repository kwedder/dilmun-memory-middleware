"""
Memory Store - File-based persistence for facts and episodes.

Provides the underlying storage layer for Dilmun Memory Middleware.
Compatible with Obsidian vault structure.
"""

import os
import json
import hashlib
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

PARTITIONS = {"fact", "decision", "episode", "conflict", "compressed"}


class MemoryStore:
    """File-based memory store with front-matter metadata."""
    
    def __init__(self, vault_path: str = "./memory"):
        self.vault_path = Path(vault_path)
        self._ensure_partitions()
    
    def _ensure_partitions(self):
        """Create partition directories if they don't exist."""
        for partition in PARTITIONS:
            (self.vault_path / partition).mkdir(parents=True, exist_ok=True)
    
    def write_fact(self, entity: str, predicate: str, value: Any, 
                   scope: Optional[str] = None, confidence: float = 1.0, ttl_days: int = 30) -> str:
        """Write a fact with entity-predicate-value structure."""
        note_id = uuid.uuid4().hex[:12]
        timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        filename = f"{timestamp}_{note_id}.md"
        filepath = self.vault_path / "fact" / filename
        
        front_matter = {
            "id": note_id,
            "partition": "fact",
            "created": datetime.now().isoformat(),
            "metadata": {
                "entity": entity,
                "predicate": predicate,
                "value": str(value),
                "scope": scope,
                "confidence": confidence,
                "expires": (datetime.now() + timedelta(days=ttl_days)).isoformat(),
            }
        }
        
        with filepath.open("w", encoding="utf-8") as f:
            f.write("---\n")
            f.write(json.dumps(front_matter, indent=2))
            f.write("\n---\n\n")
        
        return str(filepath)
    
    def read_facts(self, entity: Optional[str] = None, predicate: Optional[str] = None, 
                   scope: Optional[str] = None, min_confidence: float = 0.0) -> List[Dict]:
        """Read facts with optional filtering."""
        facts = []
        fact_dir = self.vault_path / "fact"
        
        if not fact_dir.exists():
            return facts
        
        for filepath in fact_dir.glob("*.md"):
            try:
                content = filepath.read_text(encoding="utf-8")
                meta = self._extract_front_matter(content)
                meta_data = meta.get("metadata", {})
                
                # Apply filters
                if entity and meta_data.get("entity") != entity:
                    continue
                if predicate and meta_data.get("predicate") != predicate:
                    continue
                if scope and meta_data.get("scope") != scope:
                    continue
                
                conf = meta_data.get("confidence", 1.0)
                if isinstance(conf, str):
                    conf = float(conf)
                if conf < min_confidence:
                    continue
                
                facts.append({
                    "entity": meta_data.get("entity"),
                    "predicate": meta_data.get("predicate"),
                    "value": meta_data.get("value"),
                    "confidence": conf,
                    "scope": meta_data.get("scope"),
                    "created": meta.get("created"),
                })
            except Exception:
                continue
        
        return facts
    
    def _extract_front_matter(self, content: str) -> Dict:
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