"""Lock the current environment; run only inside the project's clean development venv."""

from importlib.metadata import distribution, distributions
from pathlib import Path

from packaging.requirements import Requirement

roots = ["fastapi", "uvicorn", "numpy", "pydantic", "httpx"]
seen = set()


def visit(name):
    d = distribution(name)
    key = d.metadata["Name"].lower()
    if key in seen:
        return
    seen.add(key)
    for dep in d.requires or []:
        req = Requirement(dep)
        if not req.marker or req.marker.evaluate({"extra": ""}):
            visit(req.name)


for name in roots:
    visit(name)
Path("requirements.lock").write_text(
    "# Locked runtime dependencies, CPython 3.12.\n"
    + "\n".join(sorted(f"{n}=={distribution(n).version}" for n in seen))
    + "\n"
)
all_deps = sorted(
    (d for d in distributions() if d.metadata["Name"].lower() not in ["supplychain-mlops", "pip"]),
    key=lambda d: d.metadata["Name"].lower(),
)
Path("requirements-dev.lock").write_text(
    "# Locked development dependencies, includes runtime.\n"
    + "\n".join(f"{d.metadata['Name']}=={d.version}" for d in all_deps)
    + "\n"
)
lines = [
    "# Installed Python dependency licenses",
    "",
    "Generated from installed distribution metadata. The package license files remain authoritative.",
    "",
    "| Package | Version | Scope | Declared license |",
    "|---|---|---|---|",
]
for d in all_deps:
    license = (
        d.metadata.get("License-Expression")
        or d.metadata.get("License")
        or "; ".join(
            x.split(" :: ")[-1]
            for x in d.metadata.get_all("Classifier", [])
            if x.startswith("License ::")
        )
        or "Review distribution license file"
    )
    license = " ".join(license.split())[:180].replace("|", "/")
    lines.append(
        f"| {d.metadata['Name']} | {d.version} | {'runtime' if d.metadata['Name'].lower() in seen else 'development'} | {license} |"
    )
Path("docs/python-dependency-licenses.md").write_text("\n".join(lines) + "\n")
