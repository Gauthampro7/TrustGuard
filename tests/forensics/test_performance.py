"""Warmed bounded-input CPU latency target; timings describe this host only.

Workloads come from tests/forensics/benchmark.py: the largest v1 input for every
extractor, shaped to evaluate fully. Fixtures are built before timing. Run the
module directly for the full cold/warmed report recorded in VALIDATION.md.
"""

import pytest

from tests.forensics.benchmark import TARGET_MS, WORKLOADS, warmed

pytestmark = pytest.mark.performance


@pytest.mark.parametrize("name", list(WORKLOADS))
def test_warmed_extractor_under_150ms(name):
    row = warmed(name, repeats=20)
    print(f"{name}: median={row['medianMs']:.2f}ms p95={row['p95Ms']:.2f}ms max={row['maxMs']:.2f}ms ({row['bound']})")
    assert row["p95Ms"] < TARGET_MS, f"{name} warm p95 {row['p95Ms']:.1f}ms exceeded {TARGET_MS}ms on bounded inputs"
