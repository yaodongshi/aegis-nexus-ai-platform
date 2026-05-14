# Change: Complete Architecture Design Based on Solution A

## Why
The platform direction is now explicit: LiteLLM as the data plane, one observability layer (Langfuse preferred), and a self-built control plane for team governance and Skill/RAG registration. We need one cohesive design package that aligns interfaces, data model, deployment, operations, and rollout sequence.

## What Changes
- Define a complete target architecture for Solution A across control plane, data plane, and observability.
- Standardize API boundaries:
  - Control plane: `/api/v1/*`
  - Data plane (LiteLLM OpenAI-compatible): `/v1/*`
- Define the governance model for team, user, virtual key, model authorization, policy, and ownership.
- Define Skill/RAG cloud registry model and synchronization lifecycle.
- Define observability integration contract with Langfuse as default and Helicone as optional alternative.
- Define deployment topology, security boundaries, and phased rollout plan.

## Impact
- Affected specs: `gateway-data-plane`, `control-plane-governance`, `observability-plane`, `skill-rag-registry`
- Affected docs: `docs/user-guide-v2.md`, `docs/SOLUTION_A_COMPLETE_DESIGN.md`
- Affected code (future implementation): `backend/app/*`, `backend/migrations/*`, `scripts/*`
