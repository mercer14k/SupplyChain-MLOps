"""Optional live-runtime comparison. Requires explicit environment opt-in and model names."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scml.ai.runtime import explain  # noqa: E402
from scml.data.store import Store  # noqa: E402
from scml.evaluation.benchmark import hardware  # noqa: E402
from scml.services.config import Settings  # noqa: E402
from scml.services.lifecycle import Lifecycle, public_run  # noqa: E402

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="+", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", default="output/local-model-benchmark.json")
    args = parser.parse_args()
    settings = Settings()
    if not settings.llm_enabled:
        parser.error("Explicitly set SCML_LLM_ENABLED=true to run this optional benchmark")
    service = Lifecycle(Store(settings.root))
    run = service.require("runs", args.run_id)
    evidence = {run["id"]: public_run(run)}
    results = [explain(settings, evidence, name) for name in args.models]
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    metadata = hardware()
    metadata["local_llm"] = "enabled"
    out.write_text(
        json.dumps(
            {
                "hardware": metadata,
                "runtime": settings.llm_runtime,
                "models": args.models,
                "run_id": run["id"],
                "results": results,
            },
            indent=2,
        )
        + "\n"
    )
    print(f"Wrote {len(results)} observed results to {out}")
