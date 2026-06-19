"""Tests for Dilmun Memory Middleware."""

import tempfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from dilmun import DilmunMemoryMiddleware, MemoryStore, GradedMemoryRing


def test_memory_store_init():
    """Test memory store initialization."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = MemoryStore(tmpdir)
        assert (Path(tmpdir) / "fact").exists()
        assert (Path(tmpdir) / "decision").exists()


def test_write_and_read_fact():
    """Test basic fact storage and retrieval."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = MemoryStore(tmpdir)
        path = store.write_fact("user", "name", "Alice")
        assert Path(path).exists()
        
        facts = store.read_facts()
        assert len(facts) == 1
        assert facts[0]["entity"] == "user"
        assert facts[0]["predicate"] == "name"
        assert facts[0]["value"] == "Alice"


def test_middleware_basic():
    """Test middleware basic operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mw = DilmunMemoryMiddleware(tmpdir)
        mw.open_episode("test_session", ["chat"])
        
        mw.write_fact("user", "name", "Bob")
        context = mw.get_context()
        
        assert len(context) == 1
        assert context[0]["value"] == "Bob"
        
        mw.close_episode()


if __name__ == "__main__":
    test_memory_store_init()
    test_write_and_read_fact()
    test_middleware_basic()
    print("All tests passed!")