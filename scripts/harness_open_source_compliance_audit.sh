#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
WORKSPACE_ROOT="$(cd "${PROJECT_ROOT}/.." && pwd)"

VENV_PYTHON="${WORKSPACE_ROOT}/.venv/bin/python"
OUTPUT_PATH="${1:-${PROJECT_ROOT}/reports/harness_open_source_compliance_latest.md}"

mkdir -p "$(dirname "${OUTPUT_PATH}")"

if [[ ! -x "${VENV_PYTHON}" ]]; then
  echo "[ERROR] Missing Python interpreter: ${VENV_PYTHON}" >&2
  exit 1
fi

pushd "${PROJECT_ROOT}" >/dev/null
GIT_SHA="$(git rev-parse --short HEAD)"
popd >/dev/null

"${VENV_PYTHON}" - <<'PY' "${OUTPUT_PATH}" "${GIT_SHA}"
from __future__ import annotations

from datetime import datetime, UTC
from importlib import metadata
from pathlib import Path
import sys

output_path = Path(sys.argv[1])
git_sha = sys.argv[2]

packages = [
    "fastapi",
    "uvicorn",
    "pydantic",
    "httpx",
    "litellm",
    "langgraph",
    "openai-agents",
]

allowed_keywords = ["mit", "bsd", "apache"]
review_keywords = ["gpl", "agpl", "lgpl", "sspl", "mpl"]

rows: list[tuple[str, str, str, str]] = []
needs_review = 0

for name in packages:
    try:
        dist = metadata.distribution(name)
        version = dist.version
        license_value = (dist.metadata.get("License") or "").strip() or "UNKNOWN"
    except metadata.PackageNotFoundError:
        version = "NOT_INSTALLED"
        license_value = "UNKNOWN"

    normalized = license_value.lower()
    status = "ok"
    if any(keyword in normalized for keyword in review_keywords):
        status = "review-required"
    elif license_value == "UNKNOWN":
        status = "review-required"
    elif not any(keyword in normalized for keyword in allowed_keywords):
        status = "review-required"

    if status != "ok":
        needs_review += 1

    rows.append((name, version, license_value, status))

now = datetime.now(UTC).isoformat()
status_text = "PASS" if needs_review == 0 else "REVIEW_REQUIRED"

lines = [
    "# Harness Open-Source Compliance Report",
    "",
    f"- Generated At: {now}",
    f"- Commit: {git_sha}",
    f"- Overall Status: {status_text}",
    f"- Packages Requiring Review: {needs_review}",
    "",
    "| Package | Version | License | Status |",
    "| --- | --- | --- | --- |",
]

for name, version, license_value, status in rows:
    lines.append(f"| {name} | {version} | {license_value} | {status} |")

lines.extend(
    [
        "",
        "## Notes",
        "",
        "- `review-required` does not always block release, but requires explicit legal/owner sign-off.",
        "- `NOT_INSTALLED` packages indicate optional adapters not currently active in this environment.",
    ]
)

output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(str(output_path))
PY

echo "[OK] Compliance report generated: ${OUTPUT_PATH}"
