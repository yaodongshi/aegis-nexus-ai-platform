# Harness Open-Source License and Compliance Checklist (2026-06-02)

## Scope

This checklist covers reused open-source components for harness runtime architecture in Team AI Platform.

In scope:
- Runtime adapter layer and execution flow
- Replay and observability support tooling
- Test and CI validation for adapter behavior

Out of scope:
- Third-party SaaS terms not used as distributable software packages
- Internal-only private code under team ownership

## Reuse Policy

- Reuse architecture patterns and API contracts, not copyrighted source code copy.
- Keep module boundaries clear between upstream references and local implementation.
- Maintain immutable attribution notes for each imported dependency.
- Block production rollout when license status is unknown.

## Candidate Components and Obligations

| Component | Intended Usage | Typical License | Must Verify | Key Obligations |
| --- | --- | --- | --- | --- |
| LangGraph | Runtime orchestration reference and optional adapter target | MIT | Package LICENSE file | Keep copyright and license notice |
| OpenAI Agents SDK | Guardrail/session/tracing design reference and optional adapter target | MIT or vendor-defined in package | Package metadata and LICENSE | Follow SDK terms, keep notices |
| FastAPI | API surface | MIT | Installed package metadata | Keep notices in distribution |
| Uvicorn | ASGI server | BSD-3-Clause | Installed package metadata | Keep notices in distribution |
| Pydantic | Schema contracts | MIT | Installed package metadata | Keep notices in distribution |
| HTTPX | Runtime probes | BSD-3-Clause | Installed package metadata | Keep notices in distribution |
| LiteLLM | Gateway integration | MIT | Upstream LICENSE | Keep notices and preserve attribution |

## Compliance Workflow

1. Inventory
- Enumerate direct and critical transitive dependencies used by harness/runtime paths.
- Pin package versions in runtime requirements.

2. License Detection
- Collect installed package `Name`, `Version`, and `License` metadata.
- Flag unknown/empty license values for manual review.

3. Policy Check
- Allowed by default: MIT, BSD-2-Clause, BSD-3-Clause, Apache-2.0.
- Review-required: MPL, LGPL, AGPL, GPL, SSPL, unknown/custom licenses.

4. Attribution and Record
- Keep a release-time report under `reports/`.
- Keep checklist updates in docs whenever dependency set changes.

5. Release Gate
- Do not mark release-ready when report has unknown licenses.
- Attach compliance report to release evidence package.

## Required Evidence Per Release

- Generated compliance report file under `reports/`.
- Commit SHA and generation timestamp.
- Manual review notes for each unknown license entry.
- Approval record from architecture/release owner.

## Operational Command

Run compliance audit script:

```bash
bash scripts/harness_open_source_compliance_audit.sh
```

Optional custom output:

```bash
bash scripts/harness_open_source_compliance_audit.sh reports/harness_open_source_compliance_$(date +%Y%m%d_%H%M%S).md
```

## Current Status

- Checklist baseline created.
- Audit script created for repeatable evidence generation.
- First generated report should be committed or archived with release artifacts.
