# Change: Align Platform to LiteLLM + Qdrant Closed Loop v2

## Why
Current implementation already includes LiteLLM and Qdrant foundations, but documentation and admin IA still contain historical branches and mixed goals. This causes execution drift and governance ambiguity.

## What Changes
- Define a single master plan document for product, architecture, and business alignment.
- Introduce a centralized documentation index and archive legacy phase reports/design variants.
- Re-align admin navigation and dashboard shortcuts to AI governance core modules.
- Keep legacy business modules as compatibility entries during transition instead of immediate hard removal.
- Add MCP-driven skill bundle upload/download and team-wide sync rules as required closed-loop capability.
- Add session/CLI knowledge ingestion rules into RAG and enforce RAG-to-Skill and RAG-to-Agent evolution paths.

## Impact
- Affected specs: control-plane
- Affected code: frontend layout/navigation, dashboard entry points, README/docs governance, evolution protocol documentation
- Operational impact: lower cognitive load, clearer rollout baseline, reduced accidental usage of obsolete flows
