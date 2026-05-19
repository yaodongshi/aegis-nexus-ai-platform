# 🚀 Self-Evolution Platform: From Architecture to Implementation

**Purpose:** Guide for integrating self-evolution system into existing Team AI Platform  
**Audience:** Technical architects, backend/frontend leads, platform engineers  
**Status:** Implementation Roadmap v1.0  
**Date:** 2026-05-19

---

## Overview: The Complete System

You now have 4 layers of design:

```
Layer 1: Architecture (SOLUTION_A_COMPLETE_DESIGN.md)
  ├─ 3-plane design (control/data/observability)
  ├─ Component interactions
  └─ Deployment topology

Layer 2: System Design (COMPLETE_SELF_EVOLUTION_SYSTEM_DESIGN.md)
  ├─ 7-stage self-evolution loop
  ├─ Real-world scenarios
  ├─ Success metrics
  └─ 12-week roadmap

Layer 3: Technical Spec (VIRTUAL_KEY_CLI_IMPLEMENTATION_SPEC.md)
  ├─ Database schema
  ├─ API contracts
  ├─ CLI commands
  └─ Security considerations

Layer 4: Specifications (4 core specs in openspec/specs/)
  ├─ control-plane/spec.md
  ├─ skill-platform/spec.md
  ├─ rag-platform/spec.md
  └─ gitops-evolution-loop/spec.md
```

These layers are **interdependent**:
- Specs define WHAT (requirements)
- System design explains HOW (workflows)
- Technical spec details WHEN & WHERE (implementation)
- Architecture validates the whole system

---

## Phase 0 (Now → Week 3): Foundation

### Current State
```
✅ DONE:
  - Architecture clear (3-plane model)
  - Specifications written (4 specs)
  - System design complete (7-stage loop)
  - Technical spec ready (virtual key + CLI)
  - Traceability matrix created
  - CI/CD constraint validation automated

❌ NOT STARTED:
  - Git hooks (Stage 1)
  - RAG ingestion (Stage 1)
  - Pattern mining (Stage 3)
  - Skill proposals (Stage 4)
  - Agents (Stage 5)
  - Feedback loops (Stage 6)
```

### What to Build in Phase 0

#### Milestone 0A: RAG Foundation (Week 1)

**Backend:**
```python
# api/v1/knowledge/ingest.py
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

router = APIRouter(prefix="/knowledge", tags=["knowledge"])
embedder = SentenceTransformer("all-MiniLM-L6-v2")
qdrant_client = QdrantClient(":memory:")

@router.post("/ingest")
async def ingest_knowledge(
    payload: KnowledgeIngestRequest,
    session: Session = Depends(get_session),
    user = Depends(get_user_from_key)
):
    """
    Ingest knowledge from various sources.
    
    Called by:
    1. Git hooks (auto) → source: "git:commit"
    2. Manual API → source: "api:upload"
    3. Crawlers → source: "crawler:github"
    """
    
    # 1. Chunk content
    chunks = chunk_text(payload.content, chunk_size=512)
    
    # 2. Generate embeddings
    embeddings = [embedder.encode(chunk) for chunk in chunks]
    
    # 3. Calculate quality score
    quality_score = calculate_quality_score(
        source_type=payload.source,
        text_length=len(payload.content),
        has_code=has_code_blocks(payload.content),
        community_validation=payload.votes or 0
    )
    
    # 4. Store in DB + Qdrant
    for chunk, embedding in zip(chunks, embeddings):
        kb_entry = KnowledgeBase(
            user_id=user.id,
            source_type=payload.source,
            source_reference=payload.source_ref,
            content=chunk,
            embedding=embedding,
            quality_score=quality_score,
            tags=payload.tags or [],
            metadata={
                "author": payload.author,
                "timestamp": payload.timestamp,
                "source_url": payload.source_url
            }
        )
        session.add(kb_entry)
        
        # Add to Qdrant
        qdrant_client.upsert(
            collection_name="knowledge",
            points=[
                Point(
                    id=kb_entry.id,
                    vector=embedding,
                    payload={"quality_score": quality_score, "source": payload.source}
                )
            ]
        )
    
    session.commit()
    
    return {
        "status": "ingested",
        "count": len(chunks),
        "quality_score": quality_score,
        "collection_size": qdrant_client.count("knowledge")
    }


@router.get("/search")
async def search_knowledge(
    query: str,
    limit: int = 10,
    min_quality: float = 0.5,
    session: Session = Depends(get_session)
):
    """Semantic search across knowledge base."""
    
    # 1. Encode query
    query_embedding = embedder.encode(query)
    
    # 2. Search Qdrant
    results = qdrant_client.search(
        collection_name="knowledge",
        query_vector=query_embedding,
        limit=limit,
        query_filter=Filter(
            must=[
                HasPayloadCondition(
                    field="quality_score",
                    has_payload_condition={"gte": min_quality}
                )
            ]
        )
    )
    
    # 3. Fetch full entries from DB
    entries = []
    for result in results:
        kb = session.get(KnowledgeBase, result.id)
        entries.append({
            "id": kb.id,
            "content": kb.content,
            "source": kb.source_type,
            "quality_score": kb.quality_score,
            "similarity": result.score,
            "tags": kb.tags,
            "metadata": kb.metadata
        })
    
    return {
        "query": query,
        "results": entries,
        "total": len(entries)
    }
```

**Document Upload API (Seed Phase):**

To support front-loaded data ingestion, add document upload endpoints:

```python
# api/v1/knowledge/upload.py
from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, Depends
import tempfile
import os
from langchain.document_loaders import PyPDFLoader, Docx2docLoader

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

async def process_document_task(
    file_path: str,
    user_id: str,
    tags: list,
    session: Session
):
    """
    Background task: Parse, chunk, embed, store document.
    Supports: PDF, DOCX, Markdown, plain text, JSON
    """
    try:
        # 1. Detect format and parse
        ext = file_path.split('.')[-1].lower()
        
        if ext == 'pdf':
            loader = PyPDFLoader(file_path)
        elif ext == 'docx':
            loader = Docx2docLoader(file_path)
        else:  # Markdown, TXT, JSON
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            from langchain.schema import Document
            loader = type('TextLoader', (), {
                'load': lambda: [Document(page_content=content, metadata={"source": file_path})]
            })()
        
        docs = loader.load()
        
        # 2. Chunk and embed
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        from sentence_transformers import SentenceTransformer
        
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=512,
            chunk_overlap=50,
            separators=["\n\n", "\n", " ", ""]
        )
        
        chunks = splitter.split_documents(docs)
        embedder = SentenceTransformer("all-MiniLM-L6-v2")
        embeddings = embedder.encode(
            [c.page_content for c in chunks],
            batch_size=32
        )
        
        # 3. Check for duplicates
        from sklearn.metrics.pairwise import cosine_similarity
        existing = session.exec(
            select(KnowledgeBase.embedding)
        ).all()
        
        duplicates = []
        if existing:
            for embedding in embeddings:
                scores = cosine_similarity([embedding], existing)[0]
                if scores.max() > 0.95:
                    duplicates.append(True)
                else:
                    duplicates.append(False)
        
        # 4. Store
        quality_scores = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            if i < len(duplicates) and duplicates[i]:
                continue  # Skip duplicate
            
            # Quality: uploaded docs = 0.80 base + adjustments
            quality = 0.80
            if len(chunk.page_content) > 1000:
                quality += 0.1  # Detailed
            if chunk.page_content.count('\n') > 10:
                quality += 0.05  # Well-structured
            quality = min(quality, 1.0)
            
            quality_scores.append(quality)
            
            kb = KnowledgeBase(
                user_id=user_id,
                source_type="api:upload",
                source_reference=f"upload_{os.path.basename(file_path)}",
                content=chunk.page_content,
                embedding=embedding,
                quality_score=quality,
                tags=tags,
                metadata={
                    "author": user_id,
                    "upload_time": datetime.utcnow().isoformat(),
                    "original_file": os.path.basename(file_path)
                }
            )
            session.add(kb)
        
        session.commit()
        
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


@router.post("/upload")
async def upload_knowledge(
    file: UploadFile = File(...),
    tags: str = Form(""),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    session: Session = Depends(get_session),
    user = Depends(get_user_from_key)
):
    """
    Upload and ingest a document (PDF, DOCX, MD, TXT, JSON).
    Processing happens in background.
    """
    
    # Save temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file.filename.split('.')[-1]}") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    # Queue processing
    background_tasks.add_task(
        process_document_task,
        tmp_path,
        str(user.id),
        tags.split(",") if tags else [],
        session
    )
    
    return {
        "status": "processing",
        "filename": file.filename,
        "message": "Document queued for ingestion"
    }
```

**CLI Upload Command:**

```bash
# Single file
team ai knowledge upload ./deployment-guide.pdf --tags "deployment,guide"

# Batch import from CSV
team ai knowledge batch-import ./docs.csv --tags "team-docs"

# GitHub import
team ai knowledge import-github --owner company --repo platform --paths "docs/,README.md"
```

**Database Migration:**

```sql
-- For tracking uploads
CREATE TABLE source_documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  filename VARCHAR(255),
  file_format VARCHAR(20),
  ingestion_method VARCHAR(50),  -- api_upload, github_import, etc.
  status VARCHAR(20),  -- processing, complete, failed
  chunks_created INT,
  chunks_deduplicated INT,
  quality_scores FLOAT8[],  -- Array of scores
  created_at TIMESTAMP DEFAULT NOW()
);

ALTER TABLE knowledge_base 
  ADD COLUMN source_document_id UUID REFERENCES source_documents(id);
```


```sql
-- Knowledge base storage
CREATE TABLE knowledge_base (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  
  -- Source tracking
  source_type VARCHAR(50),  -- git:commit, api:upload, crawler:github, etc.
  source_reference VARCHAR(500),  -- commit hash, URL, etc.
  
  -- Content
  content TEXT NOT NULL,
  embedding vector(384),  -- 384-dim embeddings from all-MiniLM
  
  -- Quality
  quality_score FLOAT,  -- 0.0-1.0
  tags JSONB,  -- ["bug-fix", "performance", etc.]
  
  -- Metadata
  metadata JSONB,  -- {author, timestamp, source_url, etc.}
  created_at TIMESTAMP DEFAULT NOW(),
  
  INDEX idx_quality (quality_score),
  INDEX idx_user_created (user_id, created_at)
);

-- Qdrant handles semantic search (separate vector DB)
```

**Git Hook:**
```bash
#!/bin/bash
# .git/hooks/post-commit

VK=$(cat ~/.team/config.json | jq -r '.virtual_key' 2>/dev/null)
if [ -z "$VK" ]; then exit 0; fi

HASH=$(git rev-parse HEAD)
MSG=$(git log -1 --pretty=%B)
AUTHOR=$(git log -1 --pretty=%an)

curl -s -X POST https://platform/api/v1/knowledge/ingest \
  -H "Authorization: Bearer $VK" \
  -H "Content-Type: application/json" \
  -d "{
    \"source\": \"git:commit\",
    \"source_ref\": \"$HASH\",
    \"content\": \"$MSG\",
    \"author\": \"$AUTHOR\",
    \"tags\": [\"code-change\"],
    \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"
  }" &

exit 0
```

**Success Criteria:**
- [ ] RAG ingestion API working (test with curl)
- [ ] Document upload API working (PDF, DOCX, MD)
- [ ] Git hooks deployed to >90% of dev machines
- [ ] 500+ knowledge entries seeded via manual import
- [ ] 100+ knowledge entries ingested/day from git
- [ ] Search latency <200ms
- [ ] Quality scores calculated for all entries
- [ ] Deduplication effectiveness >95% (no false positives)

**Effort:** 2-3 people × 1 week = 10-15 person-days

---

#### Milestone 0B: Virtual Key & CLI Foundation (Week 2)

**Backend:**
```python
# api/v1/keys/router.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from cryptography.fernet import Fernet
import secrets

router = APIRouter(prefix="/keys", tags=["virtual-keys"])

@router.post("/create")
async def create_virtual_key(
    payload: CreateKeyRequest,
    session: Session = Depends(get_session),
    user = Depends(get_user)
):
    """Create new virtual key for user."""
    
    # Check for duplicates
    existing = session.exec(
        select(VirtualKey).where(
            VirtualKey.user_id == user.id,
            VirtualKey.name == payload.name
        )
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Key '{payload.name}' already exists"
        )
    
    # Generate key
    key_secret = f"vk_{int(time.time())}_{secrets.token_hex(16)}"
    key_hash = hash_pbkdf2(key_secret, iterations=100000)
    key_prefix = key_secret[:10]
    
    # Create DB entry
    vk = VirtualKey(
        user_id=user.id,
        name=payload.name,
        key_secret_hash=key_hash,
        key_public_prefix=key_prefix,
        scopes=payload.scopes or [],
        rate_limit_requests=payload.rate_limit_requests or 1000,
        expires_at=payload.expires_at,
        description=payload.description
    )
    
    session.add(vk)
    session.commit()
    
    return {
        "id": vk.id,
        "key": key_secret,  # Return only once
        "prefix": key_prefix,
        "scopes": vk.scopes,
        "created_at": vk.created_at,
        "expires_at": vk.expires_at,
        "note": "Store this key safely. You won't see it again."
    }

@router.get("/list")
async def list_virtual_keys(
    session: Session = Depends(get_session),
    user = Depends(get_user)
):
    """List all virtual keys for user."""
    
    keys = session.exec(
        select(VirtualKey).where(VirtualKey.user_id == user.id)
    ).all()
    
    return [
        {
            "id": k.id,
            "name": k.name,
            "prefix": k.key_public_prefix,
            "status": k.status,
            "scopes": k.scopes,
            "created_at": k.created_at,
            "expires_at": k.expires_at,
            "last_used_at": k.last_used_at,
            "description": k.description
        }
        for k in keys
    ]

@router.delete("/{key_id}")
async def revoke_virtual_key(
    key_id: str,
    session: Session = Depends(get_session),
    user = Depends(get_user)
):
    """Revoke virtual key (immediate & permanent)."""
    
    vk = session.get(VirtualKey, key_id)
    if not vk or vk.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Key not found"
        )
    
    vk.status = "revoked"
    vk.revoked_at = datetime.utcnow()
    session.add(vk)
    session.commit()
    
    return {"status": "revoked", "key_id": key_id}
```

**CLI (Node.js):**
```typescript
// cli/commands/key.ts
import { Command } from 'commander';
import axios from 'axios';
import chalk from 'chalk';
import * as keyring from 'keyring';

const keyCmd = new Command('key');

keyCmd
  .command('create <name>')
  .option('--scopes <scopes>', 'Comma-separated scopes')
  .option('--expires <date>', 'Expiration date (ISO 8601)')
  .action(async (name, options) => {
    try {
      const vk = await getActiveVirtualKey();
      const response = await axios.post(
        'https://platform/api/v1/keys/create',
        {
          name,
          scopes: options.scopes ? options.scopes.split(',') : [],
          expires_at: options.expires
        },
        {
          headers: { 'Authorization': `Bearer ${vk}` }
        }
      );
      
      const key = response.data.key;
      console.log(chalk.green(`✓ Key created: ${name}`));
      console.log(chalk.yellow(`  Prefix: ${response.data.prefix}`));
      console.log(chalk.yellow(`  Scopes: ${response.data.scopes.join(', ')}`));
      console.log(chalk.red.bold(`  Secret: ${key}`));
      console.log(chalk.red(`  ⚠️  Store this secret safely. You won't see it again.`));
      
      // Save to keyring
      await keyring.setPassword('team-cli', name, key);
      console.log(chalk.green(`✓ Key stored in system keyring`));
    } catch (error) {
      console.error(chalk.red('✗ Error creating key:'), error.message);
      process.exit(1);
    }
  });

keyCmd
  .command('list')
  .action(async () => {
    try {
      const vk = await getActiveVirtualKey();
      const response = await axios.get(
        'https://platform/api/v1/keys/list',
        {
          headers: { 'Authorization': `Bearer ${vk}` }
        }
      );
      
      const table = new Table({
        head: ['Name', 'Status', 'Scopes', 'Created', 'Expires'],
        colWidths: [20, 12, 30, 20, 20]
      });
      
      response.data.forEach(k => {
        table.push([
          k.name,
          k.status === 'active' ? chalk.green('✓ Active') : chalk.red('✗ ' + k.status),
          k.scopes.join(', '),
          new Date(k.created_at).toLocaleDateString(),
          k.expires_at ? new Date(k.expires_at).toLocaleDateString() : 'Never'
        ]);
      });
      
      console.log(table.toString());
    } catch (error) {
      console.error(chalk.red('✗ Error listing keys:'), error.message);
      process.exit(1);
    }
  });

keyCmd
  .command('revoke <name>')
  .action(async (name) => {
    try {
      const response = await confirm(
        chalk.yellow(`Are you sure you want to revoke key '${name}'? (cannot be undone)`)
      );
      
      if (!response) {
        console.log(chalk.gray('Cancelled'));
        return;
      }
      
      const vk = await getActiveVirtualKey();
      // Find key by name, get ID
      const keys = await getKeyList(vk);
      const keyId = keys.find(k => k.name === name)?.id;
      
      if (!keyId) {
        throw new Error(`Key '${name}' not found`);
      }
      
      await axios.delete(
        `https://platform/api/v1/keys/${keyId}`,
        {
          headers: { 'Authorization': `Bearer ${vk}` }
        }
      );
      
      console.log(chalk.green(`✓ Key '${name}' revoked`));
      
      // Remove from keyring
      await keyring.deletePassword('team-cli', name);
    } catch (error) {
      console.error(chalk.red('✗ Error revoking key:'), error.message);
      process.exit(1);
    }
  });

export default keyCmd;
```

**Success Criteria:**
- [ ] Virtual key create/list/revoke APIs working
- [ ] CLI tool installed (`npm install -g @team/platform-cli`)
- [ ] `team key create` works (stores securely)
- [ ] `team key list` displays all keys
- [ ] Rate limiting enforced (test with 1000+ requests)

**Effort:** 2 people × 1 week = 10 person-days

---

#### Milestone 0C: API Authentication (Week 3)

**Add Virtual Key Middleware:**
```python
# middleware/virtual_key_auth.py
from fastapi import Request, HTTPException, status
from functools import wraps
import time

async def verify_virtual_key(request: Request, session: Session):
    """
    Middleware: Verify virtual key on every request.
    
    Called on all protected routes: @require_auth
    """
    
    # Extract key from header
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header"
        )
    
    key_secret = auth_header[7:]  # Remove "Bearer "
    
    # Hash and look up
    key_hash = hash_pbkdf2(key_secret, iterations=100000)
    vk = session.exec(
        select(VirtualKey).where(
            VirtualKey.key_secret_hash == key_hash
        )
    ).first()
    
    if not vk:
        # Log failed attempt
        log_audit(
            virtual_key_id=None,
            endpoint=request.url.path,
            method=request.method,
            success=False,
            failure_reason="invalid_key",
            ip_address=request.client.host
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid virtual key"
        )
    
    # Check status
    if vk.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Key is {vk.status}"
        )
    
    # Check expiration
    if vk.expires_at and vk.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Key expired"
        )
    
    # Check rate limit
    if not check_rate_limit(vk):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )
    
    # Update last used
    vk.last_used_at = datetime.utcnow()
    vk.last_used_ip = request.client.host
    session.add(vk)
    
    # Log successful request
    log_audit(
        virtual_key_id=vk.id,
        endpoint=request.url.path,
        method=request.method,
        status_code=200,  # Will update after response
        success=True,
        ip_address=request.client.host
    )
    
    # Attach to request
    request.state.virtual_key = vk
    request.state.user_id = vk.user_id
    
    return vk
```

**Success Criteria:**
- [ ] All API routes require virtual key
- [ ] 401 on missing/invalid key
- [ ] 429 on rate limit exceeded
- [ ] 401 on expired key
- [ ] Audit logs created for all requests
- [ ] Response headers include rate limit info

**Effort:** 1 person × 3 days = 3 person-days

---

### Phase 0 Summary

**Total effort:** 5-10 + 10 + 3 = 18-23 person-days (~4-5 people × 1 week)

**Deliverables:**
1. ✅ RAG ingestion working (Git hooks + API)
2. ✅ Virtual Key creation & management
3. ✅ CLI tool (basic: key commands)
4. ✅ API authentication with virtual keys
5. ✅ Audit logging on all requests
6. ✅ Rate limiting enforced

**By end of Week 3:**
- Git hooks running on 90%+ of dev machines
- 500+ knowledge entries ingested
- 50+ virtual keys created
- CLI adopted by early adopters

---

## Phase 1 (Weeks 4-6): Self-Evolution Loop

Once Phase 0 is stable, implement stages 3-4 of the self-evolution loop.

### Milestone 1A: Pattern Mining (Week 4)

**Pattern Detector Jobs:**
```python
# workers/pattern_miner.py
from celery import shared_task
import logging

@shared_task
def detect_recurring_problems():
    """
    Stage 3: Find problems that happen repeatedly.
    
    Example:
      - "Connection timeout" error 3+ times in last 30 days
      - Generate insight with confidence score
      - Schedule skill proposal generation
    """
    
    session = get_session()
    
    # Query knowledge base for error patterns
    errors = session.exec("""
      SELECT 
        error_type,
        COUNT(*) as occurrence_count,
        MAX(timestamp) as latest,
        ARRAY_AGG(DISTINCT kb_id) as source_knowledge_ids
      FROM knowledge_base
      WHERE tags @> '["error"]'::jsonb
        AND created_at > NOW() - INTERVAL 30 DAY
      GROUP BY error_type
      HAVING COUNT(*) >= 3
      ORDER BY occurrence_count DESC
    """).all()
    
    for error in errors:
        # Create insight
        insight = Insight(
            type="recurring_problem",
            title=f"Problem '{error.error_type}' happening {error.occurrence_count}x/month",
            severity="high" if error.occurrence_count >= 5 else "medium",
            confidence=min(0.95, 0.5 + (error.occurrence_count * 0.15)),  # Cap at 0.95
            evidence_knowledge_ids=error.source_knowledge_ids,
            suggested_action="Create skill to fix or document workaround"
        )
        
        session.add(insight)
    
    session.commit()
    logging.info(f"Detected {len(errors)} recurring problems")

@shared_task
def detect_solution_patterns():
    """
    Stage 3: Find solutions that multiple people discovered independently.
    
    Example:
      - Issue #456: "Need error reporting feature"
      - Comments: "I built a script that works"
      - Comments: "Let me use that script too"
      - Insight: "Team consensus, don't build feature, document workaround"
    """
    pass

@shared_task
def detect_performance_regressions():
    """
    Stage 3: Find commits correlated with performance drops.
    """
    pass

# Schedule all pattern detectors
from celery.schedules import crontab

app.conf.beat_schedule = {
    'detect_recurring_problems': {
        'task': 'workers.pattern_miner.detect_recurring_problems',
        'schedule': crontab(hour=2, minute=0),  # 2 AM daily
    },
    'detect_solution_patterns': {
        'task': 'workers.pattern_miner.detect_solution_patterns',
        'schedule': crontab(hour=3, minute=0),
    },
    'detect_perf_regressions': {
        'task': 'workers.pattern_miner.detect_performance_regressions',
        'schedule': crontab(hour=4, minute=0),
    },
}
```

**Success Criteria:**
- [ ] 10+ patterns detected by end of week
- [ ] Insights created with confidence scores
- [ ] Pattern detection jobs running daily (Celery)
- [ ] No false positives >20%

---

### Milestone 1B: Skill Proposal Generation (Week 5-6)

**Proposal Generator:**
```python
# workers/skill_proposer.py
from llms import get_llm  # Anthropic/OpenAI

@shared_task
def generate_skill_proposals():
    """
    Stage 4: Convert insights → skill proposals using LLM.
    """
    
    session = get_session()
    llm = get_llm()
    
    # Get recent insights without proposals
    insights = session.exec(
        select(Insight)
        .where(Insight.status == "pending")
        .limit(10)
    ).all()
    
    for insight in insights:
        # Fetch evidence knowledge entries
        evidence_docs = session.query(KnowledgeBase).filter(
            KnowledgeBase.id.in_(insight.evidence_knowledge_ids)
        ).all()
        
        # Build prompt for LLM
        prompt = f"""
        Based on this team insight, propose a Skill (workflow template) to address it.
        
        INSIGHT:
        {insight.title}
        Confidence: {insight.confidence}
        
        EVIDENCE (from team work):
        {[doc.content[:200] + '...' for doc in evidence_docs]}
        
        Generate a Skill proposal:
        1. Name (short, actionable)
        2. Description
        3. Prompt/Code Template (if applicable)
        4. Test cases
        5. Estimated impact
        
        Return as JSON.
        """
        
        # Call LLM
        response = llm.message(prompt)
        proposal_data = json.loads(response)
        
        # Create skill proposal
        proposal = SkillProposal(
            insight_id=insight.id,
            name=proposal_data['name'],
            description=proposal_data['description'],
            prompt_template=proposal_data.get('template'),
            test_cases=proposal_data.get('test_cases'),
            confidence=insight.confidence,
            generated_by="llm",
            status="draft"
        )
        
        session.add(proposal)
        insight.status = "proposed"
        session.add(insight)
    
    session.commit()
```

**Success Criteria:**
- [ ] 5-10 skill proposals auto-generated by week 6
- [ ] Team manually reviews & approves 80%+
- [ ] Proposals have confidence scores
- [ ] LLM calls logged & tracked

---

## Phase 2 (Weeks 7-9): Agents & Automation

Implement agent generation and MCP binding.

**This is where the system becomes truly autonomous:**

```python
# workers/agent_generator.py

@shared_task
def generate_agents_from_skills():
    """
    Stage 5: Create agents from published skills.
    """
    
    session = get_session()
    
    # Get newly published skills
    new_skills = session.exec(
        select(Skill)
        .where(Skill.status == "published")
        .where(Skill.agent_generated == False)
    ).all()
    
    for skill in new_skills:
        # Determine agent type
        if skill.type == "workflow":
            agent_type = "reactive"
        elif skill.type == "code_template":
            agent_type = "code_executor"
        else:
            continue
        
        # Create agent
        agent = Agent(
            skill_id=skill.id,
            name=f"agent_{skill.name}",
            agent_type=agent_type,
            mcp_bindings={
                "logging": "internal",
                "execution": "docker" if skill.requires_env else "subprocess",
                "feedback": "metrics_db"
            },
            status="active"
        )
        
        session.add(agent)
        skill.agent_generated = True
        session.add(skill)
    
    session.commit()
```

---

## Phase 3 (Weeks 10-12): Monitoring & Feedback Loop

Implement metrics collection and self-improvement.

```python
# workers/feedback_collector.py

@shared_task
def collect_skill_feedback():
    """
    Stage 6: Collect metrics from skill executions.
    """
    
    session = get_session()
    
    # Aggregate execution data
    executions = session.exec("""
      SELECT 
        skill_id,
        AVG(execution_time_ms) as avg_time,
        COUNT(*) as execution_count,
        SUM(CASE WHEN success THEN 1 ELSE 0 END)::FLOAT / COUNT(*) as success_rate,
        AVG(user_rating) as avg_rating
      FROM skill_executions
      WHERE created_at > NOW() - INTERVAL 7 DAY
      GROUP BY skill_id
    """).all()
    
    for exec_data in executions:
        skill = session.get(Skill, exec_data.skill_id)
        
        metrics = SkillMetrics(
            skill_id=skill.id,
            period="weekly",
            execution_count=exec_data.execution_count,
            success_rate=exec_data.success_rate,
            avg_execution_time=exec_data.avg_time,
            user_satisfaction=exec_data.avg_rating,
            period_start=datetime.utcnow() - timedelta(days=7)
        )
        
        session.add(metrics)
    
    session.commit()
```

---

## Success Criteria by Phase

### Phase 0: Foundation
- ✅ RAG ingesting 100+/day
- ✅ Virtual keys used for all API access
- ✅ CLI adopted by 30%+ of team
- ✅ Git hooks running on 90%+ of machines

### Phase 1: Evolution
- ✅ 10+ patterns detected daily
- ✅ 5+ skills auto-proposed weekly
- ✅ Team approves 80%+ of proposals
- ✅ Insight → Skill time < 48 hours

### Phase 2: Automation
- ✅ 3+ agents deployed & running
- ✅ CLI adopted by 70%+ of team
- ✅ Virtual keys used for CI/CD
- ✅ Zero manual deployments (all automated)

### Phase 3: Intelligence
- ✅ All skills have metrics visible
- ✅ Team can see ROI of each skill
- ✅ Skill success rates trend upward
- ✅ System demonstrates learning (v2.0 skills better than v1.0)

---

## Critical Path Dependencies

```
Week 1  ──→ RAG Foundation
Week 2  ──→ Virtual Key & CLI ──→ Git Hooks Integration
Week 3  ──→ API Authentication
        │
Week 4  ┴──→ Pattern Mining (depends on RAG data)
Week 5  ┴──→ Skill Proposal Generation (depends on patterns)
Week 6  ┴──→ Skill Proposal Review & Publishing
        │
Week 7  ┴──→ Agent Generation (depends on published skills)
Week 8  ┴──→ MCP Binding & Integration
Week 9  ┴──→ Agent Testing & Deployment
        │
Week 10 ┴──→ Metrics Collection
Week 11 ┴──→ Feedback Loop & Improvement
Week 12 ┴──→ System Validation & Optimization
```

**Critical Paths:**
1. RAG → Patterns → Proposals → Skills (evolution loop core)
2. Virtual Keys → CLI → Git Hooks → Passive Ingestion (data collection)
3. Skills → Agents → Execution (automation layer)

---

## Team Structure (Recommended)

```
Team AI Platform: 6-8 people

Backend Team (3-4)
├─ RAG specialist (Qdrant, embeddings, semantic search)
├─ API/Auth specialist (FastAPI, virtual keys, rate limiting)
├─ LLM integration specialist (prompt engineering, Anthropic/OpenAI)
└─ Infrastructure (Celery, workers, monitoring)

Frontend Team (1-2)
├─ React/TypeScript specialist
└─ UX/UI for dashboard + skill/proposal UI

Platform Team (1-2)
├─ CLI tool development (Node.js)
└─ Git hooks & integrations

QA/DevOps (1)
├─ Testing (unit, integration, E2E)
├─ Deployment & monitoring
└─ Performance optimization
```

**Sprints:**
- 2-week sprints
- Phase 0: 1 sprint (foundation)
- Phase 1: 1.5 sprints (patterns + proposals)
- Phase 2: 1.5 sprints (agents + automation)
- Phase 3: 1 sprint (metrics + feedback)
- Total: ~5 sprints = 12 weeks

---

## Next Immediate Steps

1. **Finalize Architecture Decisions** (Before starting)
   - Confirm: Self-evolution loop is the right approach
   - Confirm: Virtual key + CLI as primary interface
   - Confirm: 12-week timeline acceptable
   
2. **Secure Resources** (Week 0)
   - Allocate team members (6-8 people)
   - Provision cloud resources (VMs, DBs, Qdrant)
   - Set up CI/CD pipeline
   
3. **Kick Off Phase 0** (Week 1)
   - Start with Milestone 0A (RAG)
   - Parallel: Planning for Milestone 0B (Virtual Keys)
   - Track progress weekly

4. **Monitor & Adjust** (Ongoing)
   - Weekly standup: blockers, progress
   - Bi-weekly retrospectives
   - Monthly architecture review

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| **Scope Creep** | Fix scope: 7 stages of evolution, no modifications |
| **Team Ramp-up** | Pair program: experienced dev + new dev on RAG |
| **LLM Costs** | Start with small models, track token usage |
| **Data Quality** | Quality scoring + manual audit of top proposals |
| **Security** | Code review all virtual key handling, penetration test |
| **Performance** | Load test: 1000 users, 100K skills, 10M knowledge entries |

---

## Success Metrics Dashboard

Track weekly:

```
┌─────────────────────────────────────┐
│ SELF-EVOLUTION PLATFORM METRICS     │
├─────────────────────────────────────┤
│                                     │
│ 📊 Phase 0 Progress                │
│ ├─ Knowledge ingested: 1,234       │
│ ├─ Virtual keys created: 23        │
│ ├─ CLI adoption: 35%               │
│ └─ API latency: 95ms (target <200) │
│                                     │
│ 🎯 Phase 1 Targets                 │
│ ├─ Patterns detected: 12           │
│ ├─ Skills proposed: 5              │
│ └─ Approval rate: 82%              │
│                                     │
│ 🚀 Overall                          │
│ ├─ Team satisfaction: 4.5/5        │
│ ├─ Time saved: 60 hrs/month        │
│ └─ Error reduction: 25%            │
│                                     │
└─────────────────────────────────────┘
```

---

## Summary

You're building a **self-evolving AI assistant for your internal team**.

**The Vision:**
```
Every day your team works
    ↓
Platform learns (RAG)
    ↓
Platform proposes improvements (Skills)
    ↓
Platform automates work (Agents)
    ↓
Your team becomes more productive
    ↓
Back to step 1 (cycle continues)
```

**The Roadmap:**
- **Phase 0 (Weeks 1-3):** Build data collection + authentication layer
- **Phase 1 (Weeks 4-6):** Implement pattern mining + skill proposals
- **Phase 2 (Weeks 7-9):** Generate agents + automate workflows
- **Phase 3 (Weeks 10-12):** Collect feedback + continuous improvement

**The Payoff:**
- Incident resolution time ↓ 50%
- Manual work ↓ 30% hours/month
- Team satisfaction ↑ 4.5/5
- Platform gets smarter every day

---

**Ready to start?** Pick your team and begin Phase 0 next week!
