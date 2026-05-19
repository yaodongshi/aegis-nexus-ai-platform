# Requirements Traceability Matrix & Decision Framework

**Date:** 2026-05-19  
**Purpose:** Map OpenSpec proposals → Core specs → Implementation artifacts & verify alignment with constraints (C1-C5)

---

## Part 1: Requirements Traceability Matrix

### Legend
- **Proposal ID:** OpenSpec change identifier
- **Core Spec:** Which of the 4 new spec files contains this requirement
- **Current Status:** not-started | in-progress | complete | blocked
- **Implementation Artifact:** Code file(s) that implement this requirement
- **Constraint Check:** References to C1-C5 architecture constraints

---

### Traceability Table

| Proposal ID | Core Spec | Requirement | Current Status | Impl. Artifact | C1 | C2 | C3 | C4 | C5 | Notes |
|-------------|-----------|-------------|-----------------|-----------------|----|----|----|----|----|----|
| update-solution-a-complete-design | control-plane | User account persistence | complete | backend/app/api/v1/users.py | ✓ | ✓ | ✓ |  | ✓ | Bootstrap admin + RBAC done |
| update-solution-a-complete-design | control-plane | RBAC enforcement | complete | backend/app/security.py | ✓ | ✓ | ✓ |  | ✓ | Role-based access control working |
| update-solution-a-complete-design | control-plane | Virtual key management | complete | backend/app/api/v1/keys.py | ✓ | ✓ | ✓ |  | ✓ | Create, revoke, hash storage done |
| update-solution-a-complete-design | control-plane | Model authorization policy | in-progress | backend/app/policies.py | ✓ | ✗ | ✓ |  | ✓ | API exists; frontend not updated |
| update-solution-a-complete-design | control-plane | Audit logging | complete | backend/app/audit.py | ✓ | ✓ | ✓ |  | ✓ | Immutable append-only logs |
| add-complete-admin-management-platform | skill-platform | Skill CRUD operations | complete | backend/app/api/v1/skills.py | ✓ | ✓ | ✓ |  | ✓ | Create, read, update (draft only) |
| add-complete-admin-management-platform | skill-platform | Skill versioning | complete | backend/app/models/skill_version.py | ✓ | ✓ | ✓ |  | ✓ | Publish, rollback, immutable versions |
| add-complete-admin-management-platform | skill-platform | Skill state lifecycle | in-progress | backend/app/models/skill.py | ✓ | ✗ | ✓ |  | ✓ | draft/published/deprecated done; archived UI missing |
| add-complete-admin-management-platform | skill-platform | Skill metrics & usage tracking | not-started | (new module) | ✗ | ✗ | ✓ |  | ✓ | Need execution logger + metrics aggregator |
| update-skill-gitops-rag-autoloop | rag-platform | Passive RAG ingestion | complete | backend/app/routers/learning.py | ✓ | ✓ | ✓ | ✓ | ✓ | POST /api/skill-sync/rag/ingest done |
| update-skill-gitops-rag-autoloop | rag-platform | Document embedding & search | complete | backend/app/vectordb.py | ✓ | ✓ | ✓ |  | ✓ | Qdrant integration working |
| update-skill-gitops-rag-autoloop | rag-platform | Quality scoring & filtering | in-progress | backend/app/rag/quality_scorer.py | ✓ | ✗ | ✓ |  | ✓ | Heuristic scorer done; feedback loop incomplete |
| update-skill-gitops-rag-autoloop | gitops-evolution-loop | Git hooks & CLI integration | not-started | (tooling) | ✗ | ✗ | ✓ | ✗ | ✓ | Critical blocker: evolution loop not visible to users |
| update-skill-gitops-rag-autoloop | gitops-evolution-loop | Bidirectional Git sync | not-started | (tooling) | ✗ | ✗ | ✓ | ✗ | ✓ | Critical blocker: "feels half-finished" symptom |
| update-skill-gitops-rag-autoloop | gitops-evolution-loop | Skill evolution proposals | not-started | (new module) | ✗ | ✗ | ✓ | ✗ | ✓ | Critical blocker: proposals not generated or surfaced |
| update-skill-gitops-rag-autoloop | gitops-evolution-loop | Approval gates & rollback | not-started | (new module) | ✗ | ✗ | ✓ | ✗ | ✓ | Critical blocker: governance layer missing |
| update-skill-gitops-rag-autoloop | gitops-evolution-loop | Evolution observability & UI | not-started | frontend/src/pages/skills/evolution-timeline | ✗ | ✗ | ✓ | ✗ | ✓ | **KEY ISSUE:** Users can't see the evolution flow |
| update-litellm-gateway-ops | control-plane | Gateway model sync | complete | backend/app/litellm_sync.py | ✓ | ✓ | ✓ |  | ✓ | Fixed in this session: deletes all duplicates |
| update-litellm-gateway-ops | control-plane | Health checks | complete | scripts/healthcheck.sh | ✓ | ✓ | ✓ |  | ✓ | Model count validation working |

---

### Summary by Constraint

**C1: Requirement Traceability** — Status: ✓ GOOD
- All proposals now linked to specs
- Each requirement has clear scenarios
- Traceability matrix complete

**C2: Documentation Sync** — Status: ⚠️ PARTIAL
- Specs created (new)
- Architecture doc updated (new)
- Frontend labels updated (in this session)
- **Missing:** RAG/Skill separation in code; Skill metrics module

**C3: Architecture Validation** — Status: ✓ GOOD
- 3 planes still balanced (control/data/observability)
- 4 specs reflect original design intent
- No architectural drift detected

**C4: Evolution Visibility** — Status: ❌ BLOCKED
- Evolution loop partially implemented (ingestion done)
- **User-facing UI completely missing**
- Users cannot see: where knowledge came from, why skills changed, evolution lineage
- **This is the root cause of "feels incomplete"**

**C5: Terminology** — Status: ✓ UPDATED
- Separated RAG ≠ Skill in frontend labels
- Specifications clarify roles
- Terminology matrix created (see SOLUTION_A_COMPLETE_DESIGN.md)

---

## Part 2: Implementation Gaps & Priorities

### Critical Blockers (Prevent Closure of "Half-Finished" Feeling)

| Gap | Why Critical | Effort | Timeline |
|-----|---|--------|----|
| **Evolution UI Timeline** | Users don't see where skill changes come from | 2-3 days | NOW |
| **Git Hooks + Sync** | Closes the GitOps loop; makes evolution real | 3-4 days | THIS WEEK |
| **Skill Proposals UI** | Users can't approve/reject evolution suggestions | 2 days | THIS WEEK |
| **Skill Metrics Dashboard** | No visibility into proposal quality/success rate | 1-2 days | NEXT WEEK |

### Medium Priority (Complete Admin Platform)

| Gap | Why Important | Effort | Timeline |
|-----|---|--------|----|
| Skill state management UI (archive feature) | Complete lifecycle | 1 day | NEXT WEEK |
| User management transfer-admin flow | Complete admin UX | 1 day | NEXT WEEK |
| Policy UI editor | Configure model access rules | 2 days | WEEK AFTER |

### Low Priority (Phase 2+)

| Gap | Why Deferred | Effort | Timeline |
|-----|---|--------|----|
| Multi-tenant support | Single-tenant sufficient for MVP | TBD | PHASE 2 |
| Cloud registry (GitHub releases) | Sharing across teams not needed yet | TBD | PHASE 2 |
| Advanced observability dashboard | Basic metrics sufficient now | 2-3 days | PHASE 2 |

---

## Part 3: Agent & MCP Decision Framework

### Question 1: What is "Agent" in your platform?

**Option A: External Consumer (IDE / CLI Tooling)**
```
Example: VS Code GitHub Copilot, command-line `ai-cli`
Role: Calls /v1/chat/completions with virtual key
Integration: No platform changes needed (already works)
```

**Option B: Internal Automation Worker**
```
Example: Evolution job, Git hook processor, RAG indexer
Role: Autonomous tasks running on backend
Integration: Needs service account + special API permissions
```

**Option C: OpenSpec Framework**
```
Example: AI assistant that helps with code review, architecture validation, documentation
Role: Development aid (not runtime component)
Integration: Completely separate from platform; documented in AGENTS.md
```

**Your Decision:** ________________________________________

---

### Question 2: What is "MCP" in your platform?

**Option A: Model Context Protocol (Anthropic Standard)**
```
Purpose: Standardized interface for AI models to access external tools/data
Your Use Case: Skill ↔ RAG communication? Or Agent ↔ Platform communication?
Integration: Requires SDK + contract definition
```

**Option B: Custom Messaging Protocol**
```
Purpose: Internal component communication
Your Use Case: Evolution job talks to RAG to get proposals?
Integration: Design custom proto/gRPC contract
```

**Option C: Not Used in MVP**
```
Reasoning: Sufficient for Phase 1 to use REST APIs + PostgreSQL
Deferral: Add MCP in Phase 2 if needed
Integration: Document as future extension point
```

**Your Decision:** ________________________________________

---

### Question 3: How Should Self-Evolution Work?

**Workflow A: Fully Automatic (Low Touch)**
```
Developer pushes code
     ↓
Git hook captures automatically
     ↓
RAG ingests silently
     ↓
Evolution job generates proposal
     ↓
IF confidence ≥0.85: auto-apply to Skill
     ↓
User sees notification: "Your skill was updated"
     ↓
User can UNDO if disagrees
```

**Workflow B: Manual Approval Gate (High Control)**
```
Developer pushes code
     ↓
Git hook captures
     ↓
RAG ingests
     ↓
Evolution job generates proposal
     ↓
ALL proposals → "pending approval" state
     ↓
User reviews + clicks [Approve] or [Reject]
     ↓
If approved: publish new skill version
     ↓
If rejected: proposal archived with feedback
```

**Workflow C: Hybrid (Recommended)**
```
Low-risk proposals (confidence ≥0.85) + policy-compliant: auto-apply
     ↓
High-risk proposals (confidence <0.85) or policy-violating: manual gate
     ↓
All logged with full traceability
```

**Your Decision:** ________________________________________

---

## Part 4: Next Immediate Actions

Based on the above, here's the prioritized checklist:

- [ ] **User Decision:** Fill in your Agent/MCP/Evolution workflow decisions above
- [ ] **Then:** I'll create `/openspec/project.md` with Agent/MCP definitions
- [ ] **Then:** Implement Critical Blockers (Evolution UI, Git hooks, Skill proposals) in this order:
  1. **Day 1:** Evolution Timeline UI (show where changes come from)
  2. **Day 2-3:** Git hooks + bidirectional sync
  3. **Day 4-5:** Skill proposals approval UI
  4. **Day 6:** Metrics dashboard

- [ ] **Constraint Enforcement:** After each feature, verify C1-C5:
  - C1: Does it trace back to spec requirement?
  - C2: Is documentation updated?
  - C3: Does it maintain 3-plane balance?
  - C4: Is evolution visible to users?
  - C5: Terminology consistent?

---

## Part 5: Long-Term Health Check (Quarterly)

Every 90 days, audit:

1. **Architecture Alignment:** Are we still following Solution A (control/data/observability 3 planes)?
2. **Requirement Drift:** Have any new features added without updating specs?
3. **Constraint Violations:** Have any of C1-C5 been violated? If yes, fix immediately.
4. **Documentation Freshness:** Is project.md still accurate? Specs up-to-date?
5. **User Feedback:** Are users still saying "half-finished"? If yes, visibility issues remain.

**Recommended:** Automate this via GitHub Actions PR check + quarterly manual review.

---

**Document Status:** ACTIVE  
**Approval Gate:** User must fill Part 3 decisions before next sprint  
**Next Update:** After Agent/MCP clarification or end of current sprint
