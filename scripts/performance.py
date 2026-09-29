"""Scale the same evaluation workload, with an explicit dataset size and metadata."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scml.evaluation.benchmark import benchmark  # noqa: E402

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--series", type=int, default=40)
    p.add_argument("--days", type=int, default=365)
    p.add_argument("--repeats", type=int, default=3)
    p.add_argument("--output", default="output/performance")
    a = p.parse_args()
    benchmark(a.output, a.days, a.series, a.repeats)
