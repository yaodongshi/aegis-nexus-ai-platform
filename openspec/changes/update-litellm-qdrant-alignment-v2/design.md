## Context
The platform evolved rapidly through multiple phases and produced valuable but overlapping documents and UI entry points. We now need a single operational baseline centered on LiteLLM + Qdrant and governance-first usage.

## Goals / Non-Goals
- Goals:
  - Establish one source of truth for architecture and execution.
  - Reduce admin console cognitive load by prioritizing core governance modules.
  - Preserve compatibility paths while de-emphasizing non-core modules.
- Non-Goals:
  - No immediate hard deletion of legacy APIs.
  - No runtime protocol break for existing clients.

## Decisions
- Decision: Introduce a master-plan document and docs index as governance baseline.
- Decision: Archive obsolete/phase-specific docs under dated archive folder.
- Decision: Keep compatibility entries for legacy modules but move them out of primary IA.

## Risks / Trade-offs
- Risk: Users accustomed to old menu layout may need adaptation.
  - Mitigation: keep compatibility routes and labels.
- Risk: Historical docs still referenced externally.
  - Mitigation: preserve files in archive with clear supersession notice.

## Migration Plan
1. Publish master plan and docs index.
2. Archive superseded docs.
3. Reorder navigation and dashboard links.
4. Validate frontend build and service health.

## Open Questions
- When should compatibility modules be fully removed from navigation?
- Should legacy API groups get explicit deprecation headers in responses?
