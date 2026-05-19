# Frontend Architecture: Separating RAG & Skill Platforms

**Date:** 2026-05-19  
**Purpose:** Design clear separation of RAG (Knowledge Base) and Skill (Prompt Management) frontends to eliminate confusion

---

## Current State (Problem)

```
Frontend Navigation:
  ├─ 知识库 & 技能  ← CONFUSED: mixing two entirely different concepts
     ├─ Tab: 知识库 (RAG docs)
     └─ Tab: 技能库 (Skills)

Problem:
- Single menu entry suggests RAG + Skill are one concept
- User doesn't understand when to use which
- Skill proposals (from RAG) are not visible in evolution flow
```

---

## Target State (Solution)

### New Frontend Structure

```
Frontend Navigation (Updated):
  ├─ 知识库 (RAG Platform)
  │   ├─ 我的文档 (My Ingested Documents)
  │   ├─ 搜索知识 (Semantic Search)
  │   ├─ 知识统计 (Knowledge Metrics)
  │   └─ 关联的技能 (Linked Skills)
  │
  ├─ 技能管理 (Skill Platform)
  │   ├─ 我的技能 (My Skills)
  │   ├─ 创建技能 (Create Skill)
  │   ├─ 版本历史 (Version History)
  │   ├─ 进化提议 (Evolution Proposals) ← KEY: where AI suggestions appear
  │   └─ 性能指标 (Performance Metrics)
  │
  ├─ 设置 (Settings)
  │   ├─ 用户管理 (User Management)
  │   ├─ 模型授权 (Model Policies)
  │   └─ 系统设置 (System Settings)
```

---

## Component Architecture

### Page 1: RAG Platform (`/knowledge`)

**Purpose:** Browse, search, and understand knowledge base

**Layout:**
```
┌─────────────────────────────────────────────────┐
│ 知识库 (RAG Platform)                          │
├─────────────────────────────────────────────────┤
│                                                 │
│ 📊 Knowledge Stats (Top Bar)                   │
│  • Total Documents: 342                        │
│  • Avg Quality Score: 0.76                     │
│  • Last Ingested: 2 hours ago                 │
│                                                 │
│ [搜索]  Search Query  ────→ 🔍                │
│                                                 │
│ Tabs:                                          │
│  📄 最近文档 (Recent)  |  🏷️ 按标签 (Tags)  │
│                                                 │
├─────────────────────────────────────────────────┤
│ Document List:                                  │
├─ [高质量] "Fix sentiment classifier" (0.89)   │
│  Source: Git commit abc123 (2hrs ago)         │
│  Keywords: sentiment, edge-case, classifier   │
│  [📖 详情] [关联技能] [反馈质量]              │
│                                                 │
├─ [中质量] "Customer feedback analysis" (0.72) │
│  Source: User experiment exp-456 (1d ago)    │
│  Keywords: analysis, feedback, metrics        │
│  [📖 详情] [关联技能] [反馈质量]              │
│                                                 │
├─ [低质量] "Draft notes" (0.23) [已过滤]      │
│  Source: Session note (filtered, quality<0.5)│
│                                                 │
└─────────────────────────────────────────────────┘
```

**Key Features:**
1. **Quality Score Badge** (色标)
   - 🟢 High (≥0.75): Green badge, appears in skill proposals
   - 🟡 Medium (0.5-0.75): Yellow badge, optional in proposals
   - 🔴 Low (<0.5): Red/filtered, hidden by default

2. **Source Attribution** (来源清晰)
   - Git commit: "Fix X" + commit SHA + link to repo
   - PR: "#123 merged" + PR link
   - Experiment: "experiment-id" + timestamp
   - User session: "session uploaded by user-name"

3. **Linked Skills** (与技能的关联)
   - Shows: "This doc influenced skill 'analyze-sentiment' v1.1"
   - Click: Jump to skill detail page

4. **Quality Feedback** (质量反馈)
   - User can click "这个文档对我没用" (not useful)
   - System uses feedback to retrain quality scorer

---

### Page 2: Skill Platform - List (`/skills`)

**Purpose:** Manage and evolve prompt templates

**Layout:**
```
┌─────────────────────────────────────────────────┐
│ 技能管理 (Skill Platform)                       │
├─────────────────────────────────────────────────┤
│                                                 │
│ [✨ 创建新技能] [导入技能]                     │
│                                                 │
│ Tabs:                                          │
│  ⚙️ 草稿 (3)  |  📤 已发布 (5)  |  📉 已废弃 (1) │
│                                                 │
├─────────────────────────────────────────────────┤
│ Skill List (Published Tab):                   │
│                                                 │
│ 1. analyze-sentiment ⭐ v1.2                  │
│    状态: [已发布]  质量: ⭐⭐⭐⭐ (92% 成功率)│
│    标签: #nlp #classification                 │
│    最后更新: "From proposal #127" (2d ago)   │
│    [📖 详情] [版本历史] [性能指标]            │
│                                                 │
│ 2. extract-entities    v1.0                   │
│    状态: [已发布]  质量: ⭐⭐⭐ (78% 成功率)  │
│    标签: #ner                                  │
│    最后更新: Manual edit by @alice (5d ago)  │
│    [📖 详情] [版本历史] [性能指标]            │
│                                                 │
└─────────────────────────────────────────────────┘
```

**Key Elements:**
1. **Version Badge** — v1.0, v1.1, etc.
2. **State Badge** — draft/published/deprecated/archived
3. **Success Rate** — % of successful executions (from metrics)
4. **Source Link** — "From proposal #X" or "Manual edit"
5. **Update Timestamp** — Clear "last changed when/by whom"

---

### Page 3: Skill Platform - Detail (`/skills/{id}`)

**Purpose:** View, edit, evolve individual skill

**Layout:**
```
┌────────────────────────────────────────────────────┐
│ Skill: "analyze-sentiment" | Version: 1.2         │
├────────────────────────────────────────────────────┤
│                                                    │
│ State: 📤 Published  |  Success Rate: 92%          │
│ Created by: @alice (2026-04-01)                   │
│ Last updated: From proposal #127 (2026-05-18)    │
│                                                    │
│ [✏️ Edit] [📋 版本历史] [📊 性能指标]             │
│ [➕ 新草稿] [🔄 回滚] [📉 弃用]                  │
│                                                    │
├─ Tabs: ────────────────────────────────────────────┤
│  📝 提示内容 (Prompt Content)                     │
│  💡 进化提议 (Evolution Proposals) [3 pending]   │
│  🔗 关联知识 (Linked Knowledge)                   │
│  📊 执行指标 (Metrics)                           │
│  ⏱️ 时间线 (Evolution Timeline)                  │
│                                                    │
├─ Tab: Evolution Proposals ──────────────────────────┤
│                                                    │
│ Pending Proposals [3]:                           │
│                                                    │
│ Proposal #128 [🟢 High Confidence: 0.91]         │
│  ├─ Suggested Change:                            │
│  │  "Add edge-case examples from recent commits" │
│  │                                                │
│  ├─ 来源知识 (Source Knowledge):                 │
│  │  • Commit abc123: "Fix sentiment edge case"   │
│  │  • Experiment exp-456: "Test results"         │
│  │  [查看知识库]                                  │
│  │                                                │
│  ├─ 自动测试结果 (Test Results):                 │
│  │  ✓ No regression detected (success rate ↑ 2%) │
│  │  [运行完整测试套件]                            │
│  │                                                │
│  └─ [✅ 批准] [❌ 拒绝]                          │
│                                                    │
│ Proposal #129 [🟡 Medium Confidence: 0.68]       │
│  └─ (similar structure)                           │
│                                                    │
│ Rejected Proposals [1]:                          │
│  ✗ Proposal #126 [Rejected 2026-05-17]          │
│    Reason: "Too aggressive, breaks backward compat"│
│    [查看详情]                                     │
│                                                    │
├─ Tab: Evolution Timeline ──────────────────────────┤
│                                                    │
│ Timeline (reverse chronological):                 │
│                                                    │
│ 2026-05-18 | 📤 Version v1.2 Published           │
│             From: Proposal #127 (auto-approved)   │
│             Confidence: 0.89                      │
│             [看提议] [对比 v1.1]                 │
│                                                    │
│ 2026-05-15 | 🔄 Rollback to v1.0                 │
│             Reason: Performance regression       │
│             [撤销回滚]                            │
│                                                    │
│ 2026-05-10 | 📤 Version v1.1 Published           │
│             Manual edit by @bob                   │
│             [看变更] [对比 v1.0]                 │
│                                                    │
│ 2026-04-01 | ✏️ Version v1.0 Created             │
│             Manual creation by @alice             │
│             [看提议]                              │
│                                                    │
└────────────────────────────────────────────────────┘
```

**Key Sections:**
1. **Evolution Proposals Tab** — AI suggestions (confidence score, source docs, test results)
2. **Timeline Tab** — Shows all changes (manual edits, auto-proposals, rollbacks)
3. **Linked Knowledge Tab** — Which RAG docs influenced this skill
4. **Metrics Tab** — Success rate, execution count, trends

---

### Critical: Evolution Timeline UI

**Why This Solves "半成品" (Half-Finished) Feeling:**

```
User's mental model BEFORE timeline:
  "I have a Skill. Where did it come from? IDK. How did it improve? Magic?"

User's mental model AFTER timeline:
  "My skill was based on code changes in commit abc123.
   When engineer fixed the edge case, the evolution system noticed,
   searched the knowledge base, generated a proposal,
   I approved it, and now my skill is better.
   I can see the full lineage!"
```

---

## Implementation Checklist

### Phase 1 (This Week): Frontend UI Separation

- [ ] Rename "知识库 & 技能" → separate "知识库" + "技能管理" menu items
- [ ] Create new `/knowledge` page (RAG platform)
  - [ ] Document list with quality badges
  - [ ] Semantic search UI
  - [ ] Link to related skills
- [ ] Move skill CRUD to separate `/skills` page
  - [ ] List view (as above)
  - [ ] Detail view skeleton
- [ ] Update navigation in `MainLayout.tsx`
- [ ] Ensure no broken routes (test all links)

### Phase 2 (Next Week): Evolution Visibility

- [ ] Create Evolution Proposals Tab in skill detail
  - [ ] Show pending proposals with confidence scores
  - [ ] Show source knowledge artifacts
  - [ ] [Approve] / [Reject] buttons (backend API exists)
  - [ ] Show test results
- [ ] Create Evolution Timeline Tab
  - [ ] Chronological log of all changes
  - [ ] Each entry shows: action, timestamp, actor, source (if automated)
  - [ ] Clickable links to related artifacts (Git commit, knowledge doc)
- [ ] Add Skill Metrics Tab
  - [ ] Success rate, execution count, trends

### Phase 3 (Week After): API & Backend Updates

- [ ] Ensure backend returns proposal details + source links
- [ ] Ensure backend returns evolution timeline
- [ ] Ensure backend returns skill metrics
- [ ] Add unit tests for timeline generation

---

## File Changes Required

### Frontend Files to Modify

```
frontend/src/
├─ layouts/MainLayout.tsx
│  └─ Change: Update nav from "知识库 & 技能" to separate menu items
│
├─ pages/
│  ├─ knowledge/ (NEW FOLDER)
│  │  ├─ index.tsx (Knowledge list page)
│  │  ├─ search.tsx (Semantic search)
│  │  └─ [id].tsx (Document detail)
│  │
│  ├─ skills/ (RENAME from existing "knowledge")
│  │  ├─ index.tsx (Skills list)
│  │  ├─ [id].tsx (Skill detail) - EXTEND with tabs
│  │  ├─ [id]/proposals.tsx (Evolution proposals sub-component)
│  │  ├─ [id]/timeline.tsx (Evolution timeline sub-component)
│  │  └─ [id]/metrics.tsx (Skill metrics sub-component)
│  │
│  └─ settings/
│     └─ index.tsx (unchanged)
│
├─ components/
│  ├─ QualityBadge.tsx (NEW: display score badges)
│  ├─ SourceAttribution.tsx (NEW: show where doc came from)
│  ├─ ProposalCard.tsx (NEW: evolution proposal display)
│  ├─ TimelineEvent.tsx (NEW: evolution timeline entry)
│  └─ SkillMetrics.tsx (NEW: success rate, trends)
│
└─ lib/
   └─ api.ts (update to include new endpoints:
      - GET /api/v1/skills/{id}/proposals
      - GET /api/v1/skills/{id}/evolution-timeline
      - GET /api/v1/skills/{id}/metrics
   )
```

---

## API Contracts Needed (Already defined in specs, confirm backend has them)

| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `/api/v1/knowledge` | GET | List docs | ✓ exists |
| `/api/v1/knowledge/search` | POST | Semantic search | ✓ exists |
| `/api/v1/skills/{id}` | GET | Skill detail | ✓ exists |
| `/api/v1/skills/{id}/proposals` | GET | List proposals | ❌ **NEED TO ADD** |
| `/api/v1/skills/{id}/proposals/{pid}/approve` | POST | Approve proposal | ❌ **NEED TO ADD** |
| `/api/v1/skills/{id}/evolution-timeline` | GET | Timeline events | ❌ **NEED TO ADD** |
| `/api/v1/skills/{id}/metrics` | GET | Usage metrics | ❌ **NEED TO ADD** |
| `/api/v1/knowledge/{id}/related-skills` | GET | Which skills use this doc | ❌ **NEED TO ADD** |

---

## Why This Matters

**Before this separation:**
```
User: "Why does my knowledge base have a 'skill view' tab?"
System: (No clear answer) ❌
Result: Platform feels incomplete
```

**After this separation:**
```
User: "I want to improve my skills based on recent learnings"
System: 
  1. Go to "知识库" → see recent commits/experiments (knowledge base)
  2. Go to "技能管理" → see pending proposals from that knowledge
  3. Click "Evolution Timeline" → see full lineage of how skill evolved
Result: Platform feels complete and purposeful ✓
```

---

**Document Status:** IMPLEMENTATION SPEC  
**Approval Gate:** User confirms design before frontend work starts
