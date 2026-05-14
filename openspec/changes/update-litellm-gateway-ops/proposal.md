# Change: Standardize LiteLLM Gateway Operations

## Why
Provider changes are already synced to `litellm/config.yaml` and `.env.litellm`, but operators still rely on ad-hoc manual commands to apply and verify gateway updates. This makes rollout and troubleshooting inconsistent.

## What Changes
- Add a dedicated script to apply gateway config updates and validate `/v1/models`.
- Enhance health checks with optional gateway models check when `LITELLM_MASTER_KEY` is available.
- Update startup output and docs to use standardized operational steps.
- Fix admin token variable naming in user docs to match runtime config.

## Impact
- Affected specs: `gateway-operations`
- Affected code: `scripts/start.sh`, `scripts/healthcheck.sh`, new `scripts/apply_litellm_gateway.sh`, `README.md`, `docs/user-guide.md`
