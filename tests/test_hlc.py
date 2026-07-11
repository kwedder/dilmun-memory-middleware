"""Tests for the Hybrid Logical Clock (dilmun/hlc.py).

    * local stamps are strictly monotonic (counter bumps when physical time stalls)
    * physical time advancing resets the counter and tracks real time
    * receive() guarantees the next local stamp is strictly after a peer's
    * pack/unpack round-trips and preserves order
    * MONEY TEST: with HLC timestamps, the REAL LWWMap picks the causally-latest
      write even under heavy clock skew (the swarm-sim Part B failure, now fixed)
"""

from pathlib import Path
import sys
import random

sys.path.insert(0, str(Path(__file__).parent.parent))

from dilmun.hlc import HLC, HLCTimestamp, stamp_fact, observe_fact, happens_before, concurrent
from dilmun.crdt import LWWMap


# ---------------------------------------------------------------------------
# clock mechanics
# ---------------------------------------------------------------------------

def test_local_monotonic_when_physical_time_stalls():
    clk = HLC("A")
    # feed the same physical time repeatedly -> counter must climb
    t0 = 1000.0
    a = clk.local(now=t0)
    b = clk.local(now=t0)
    c = clk.local(now=t0)
    assert a < b < c
    assert (a.l, a.c, b.c, c.c) == (1_000_000, 0, 1, 2)  # ms, counter 0->1->2


def test_physical_advance_resets_counter():
    clk = HLC("A")
    clk.local(now=1000.0)                 # l=1_000_000, c=0
    r = clk.local(now=1001.0)             # physical jumps forward
    assert r.l == 1_001_000 and r.c == 0


def test_receive_advances_past_peer():
    a, b = HLC("A"), HLC("B")
    # B's clock is far ahead in physical time
    peer = b.local(now=5000.0)
    # A hears it while its own physical time is behind
    a.receive(peer, now=1000.0)
    nxt = a.local(now=1000.0)
    assert nxt > peer               # A's next stamp is strictly after B's


def test_pack_unpack_roundtrip_and_order():
    for l, c in [(0, 0), (1_000_000, 5), (1_750_000_000_000, 12345)]:
        ts = HLCTimestamp(l, c)
        assert HLCTimestamp.unpack(ts.pack()) == ts
    # packing preserves lexicographic order
    assert HLCTimestamp(10, 9).pack() < HLCTimestamp(11, 0).pack()
    assert HLCTimestamp(10, 0).pack() < HLCTimestamp(10, 1).pack()


def test_concurrency_hook_is_total_order():
    a = HLCTimestamp(10, 0)
    b = HLCTimestamp(10, 1)
    assert happens_before(a, b)
    assert not concurrent(a, b)     # HLC total order: nothing flagged concurrent (yet)


# ---------------------------------------------------------------------------
# MONEY TEST — HLC fixes the swarm clock-skew crosstalk on the real LWWMap
# ---------------------------------------------------------------------------

def test_hlc_picks_causally_latest_under_clock_skew():
    rng = random.Random(7)
    trials, chain, n_robots = 2000, 6, 8
    correct = 0
    for _ in range(trials):
        clocks = {r: HLC(f"r{r}") for r in range(n_robots)}
        skew = {r: rng.gauss(0, 5.0) for r in range(n_robots)}   # big drift
        m = LWWMap()
        base = 1000.0
        truth = None
        prev_ts = None
        for i in range(chain):
            r = rng.randrange(n_robots)
            clk = clocks[r]
            # causal: this writer first *hears* the previous write, then writes
            if prev_ts is not None:
                clk.receive(prev_ts, now=base + i + skew[r])
            f = stamp_fact(clk, "k", "p", f"u{i}", now=base + i + skew[r], seq=i)
            m = m.put(f)
            prev_ts = HLCTimestamp.unpack(int(f.timestamp))
            truth = f"u{i}"
        correct += (m.get("k", "p").value == truth)
    # HLC must be perfect (the sim's wall-clock version scored 0.27-0.76 here)
    assert correct == trials, f"HLC mispicked {trials - correct}/{trials}"


def test_deterministic_given_same_physical_inputs():
    def run():
        clk = HLC("A")
        return [clk.local(now=1000.0 + i * 0.0).pack() for i in range(4)]
    assert run() == run()
