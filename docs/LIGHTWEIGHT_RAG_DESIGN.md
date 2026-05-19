# 🧠 Lightweight RAG Platform Design: Knowledge Ingestion & Management

**Purpose:** Design efficient knowledge base ingestion system for Team AI Platform  
**Reference:** RAG-Anything (GitHub), LlamaIndex, LangChain + Qdrant patterns  
**Status:** Lightweight Design v1.0  
**Date:** 2026-05-19

---

## Overview: Three Data Sources

```
┌─────────────────────────────────────────────────────────┐
│                  KNOWLEDGE INGESTION                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ Source 1: PASSIVE (Auto-Collection)                    │
│ ├─ Git commits (via hooks)                             │
│ ├─ Pull requests (via webhooks)                        │
│ ├─ Issues (via webhooks)                               │
│ └─ Chat messages (Slack integration)                   │
│ ↓ Continuous, no manual effort                         │
│                                                         │
│ Source 2: ACTIVE MANUAL (Documents)                    │
│ ├─ Upload via Web UI (drag & drop)                     │
│ ├─ Bulk import via API (batch CSV/JSON)               │
│ ├─ GitHub integration (import README, docs)           │
│ └─ Confluence/Notion sync (if using)                  │
│ ↓ User-triggered, front-loaded data                    │
│                                                         │
│ Source 3: SCHEDULED CRAWLING (Repositories)            │
│ ├─ GitHub repo documentation                          │
│ ├─ Internal wiki/documentation sites                  │
│ ├─ Code repositories (code patterns)                  │
│ └─ Meeting recordings (transcription + summary)       │
│ ↓ Periodic, background collection                      │
│                                                         │
│         ↓↓↓ All sources converge ↓↓↓                   │
│                                                         │
│       UNIFIED RAG PROCESSING PIPELINE                  │
│       ├─ Document parsing (multi-format support)      │
│       ├─ Chunking & overlap management                │
│       ├─ Embedding generation                         │
│       ├─ Deduplication                                │
│       ├─ Quality scoring                              │
│       └─ Qdrant vector storage                        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Architecture: Lightweight & Modular

### Why Lightweight?

Instead of building a full-featured RAG platform, we use **composable open-source components**:

```
Heavy (NOT our approach):
  - Build from scratch
  - Implement chunking, embedding, search from zero
  - Months of engineering

Lightweight (OUR approach):
  - Use proven libraries (LlamaIndex, Qdrant)
  - Focus on integration & data pipeline
  - Weeks of engineering
  - Lower maintenance
```

### Component Stack

```yaml
Data Ingestion Layer:
  File Upload:
    - Web UI (React drag-drop)
    - API: POST /api/v1/knowledge/upload
    - Formats: PDF, DOCX, MD, TXT, CSV, JSON
    - Library: pdf2image, python-docx, pypandoc

Parsing & Chunking:
  - LangChain Document Loaders (multi-format)
  - Simple splitting: 512 token chunks, 50 token overlap
  - Custom splitters for code (keep function blocks together)

Embedding Generation:
  - SentenceTransformers (all-MiniLM-L6-v2)
  - Lightweight: ~384 dims, fast inference
  - Batched: 100 documents at a time
  - GPU optional (works on CPU)

Vector Storage:
  - Qdrant (lightweight, Docker-friendly)
  - In-memory for dev, persistent disk for prod
  - 100K+ documents easily handled

Deduplication & Quality:
  - Semantic deduplication (embeddings > 0.95 similarity = duplicate)
  - Quality score: source_type × recency × community_validation
  - Archive old knowledge (>30 days, score <0.3)

Search & Retrieval:
  - Semantic search: ANN (Approximate Nearest Neighbors)
  - Hybrid search: semantic + keyword (BM25)
  - Top-K retrieval: return top 10 by default
```

---

## Data Models

### Knowledge Entry Schema

```python
# Core schema (in PostgreSQL)
class KnowledgeEntry:
    id: UUID                    # Unique identifier
    
    # Content
    original_document_id: UUID  # References source doc
    chunk_index: int            # Position in document (doc_id + chunk_001)
    content: str                # Actual text content
    chunk_length: int           # Tokens in this chunk
    
    # Embedding
    embedding: Vector(384)      # Vector for semantic search
    embedding_model: str        # "all-MiniLM-L6-v2" version
    
    # Source tracking
    source_type: str            # git:commit | api:upload | crawler:github | etc.
    source_reference: str       # commit hash | file path | URL
    source_url: str             # Direct link to original source
    document_title: str         # Inferred or provided title
    
    # Quality & relevance
    quality_score: float        # 0.0-1.0 (calculated)
    relevance_tags: List[str]   # ["bug-fix", "performance", "database"]
    language: str               # "en", "zh", "fr"
    
    # Metadata
    author: str                 # Who created it
    created_at: DateTime        # When ingested
    original_date: DateTime     # When the knowledge was created
    updated_at: DateTime        # When last updated
    access_count: int           # How many times searched/used
    
    # Deduplication
    canonical_id: UUID          # Points to canonical if duplicate
    is_duplicate: bool
    duplicate_score: float      # Similarity to canonical
    
    # Lifecycle
    status: str                 # "active" | "archived" | "deprecated"
    archived_at: DateTime
    archive_reason: str         # why archived

# Source document (tracks raw uploads/imports)
class SourceDocument:
    id: UUID
    user_id: UUID               # Who uploaded/triggered import
    
    # Document info
    filename: str
    file_format: str            # "pdf" | "docx" | "md" | "json"
    file_size_bytes: int
    content_hash: str           # SHA256 for dedup
    
    # Ingestion details
    ingestion_method: str       # "api_upload" | "github_import" | "crawler"
    ingestion_time_seconds: int # How long to process
    
    # Results
    chunks_created: int         # How many knowledge entries generated
    chunks_deduplicated: int    # How many were duplicates (not stored)
    quality_scores: List[float] # Score distribution
    
    # Status
    status: str                 # "processing" | "complete" | "failed"
    error_message: str          # If failed, why

# Batch import job
class BatchImportJob:
    id: UUID
    user_id: UUID
    
    # Job details
    name: str                   # "Q2 2024 documentation" 
    description: str
    csv_or_json_url: str        # URL to import file
    
    # Processing
    started_at: DateTime
    completed_at: DateTime
    status: str                 # "pending" | "processing" | "complete" | "failed"
    
    # Results
    total_rows: int
    successful_imports: int
    failed_imports: int
    errors: List[str]           # First 10 errors
    
    # Metadata
    tags_to_apply: List[str]    # Apply to all imported docs
```

---

## API Design: Document Import Endpoints

### 1. Single File Upload

```
POST /api/v1/knowledge/upload
Authorization: Bearer {virtual_key}
Content-Type: multipart/form-data

Form fields:
  - file (required): Binary file (PDF, DOCX, MD, TXT, CSV, JSON)
  - title (optional): Override detected title
  - tags (optional): Comma-separated tags (bug-fix, performance, etc.)
  - source_type (optional): "user:upload" (default) | "user:import"
  - visibility (optional): "private" | "team" | "public"

Response (202 Accepted):
{
  "import_job_id": "job_20260519_abc123",
  "filename": "deployment-guide.pdf",
  "estimated_time_seconds": 30,
  "check_status_url": "/api/v1/knowledge/import-status/{import_job_id}",
  "status": "processing"
}

# Later: Check status
GET /api/v1/knowledge/import-status/{import_job_id}
Response:
{
  "status": "complete",
  "chunks_created": 47,
  "chunks_deduplicated": 3,
  "knowledge_entries": [
    {"id": "kb_001", "title": "Deployment prerequisites", "quality": 0.92},
    ...
  ],
  "time_elapsed_seconds": 28,
  "embedding_time_seconds": 15,
  "dedup_time_seconds": 8
}
```

### 2. Batch Import (CSV)

```
POST /api/v1/knowledge/batch-import
Authorization: Bearer {virtual_key}
Content-Type: application/json

{
  "name": "Team documentation Q2",
  "csv_url": "s3://bucket/docs-to-import.csv",
  "tags": ["team-doc", "q2-2024"],
  "import_settings": {
    "skip_duplicates": true,
    "confidence_threshold": 0.7,
    "chunk_size": 512
  }
}

# CSV format expected:
title, content, source_url, date, author, tags
"API Guide", "How to use...", "https://...", "2024-01-15", "john.doe", "api,guide"
...

Response (202 Accepted):
{
  "batch_job_id": "batch_20260519_xyz",
  "total_rows": 156,
  "estimated_time_minutes": 5,
  "status": "queued"
}

# Track progress
GET /api/v1/knowledge/batch-import/{batch_job_id}
Response:
{
  "status": "processing",
  "progress_percent": 45,
  "processed_so_far": 70,
  "successful": 68,
  "failed": 2,
  "current_file": "docs-to-import.csv (row 70/156)",
  "elapsed_seconds": 120
}
```

### 3. GitHub Repository Import

```
POST /api/v1/knowledge/import-github
Authorization: Bearer {virtual_key}
Content-Type: application/json

{
  "owner": "company",
  "repo": "platform",
  "branch": "main",
  "paths": ["docs/", "README.md"],  # What to import
  "tags": ["platform-core", "github-import"],
  "skip_binary": true
}

Response (202 Accepted):
{
  "import_job_id": "github_20260519_abc",
  "repository": "company/platform",
  "estimated_files": 34,
  "estimated_time_seconds": 60,
  "status": "queued"
}
```

### 4. Search Endpoint (Already Described)

```
GET /api/v1/knowledge/search?query=batch+processor&limit=10&min_quality=0.5
Response:
{
  "query": "batch processor",
  "results": [
    {
      "id": "kb_001",
      "content": "Batch processor handles...",
      "source": "github:commit:a1b2c3d4",
      "quality_score": 0.92,
      "relevance_score": 0.87,
      "source_url": "https://github.com/.../commit/a1b2c3d4",
      "created_at": "2026-05-15T10:30:00Z",
      "tags": ["batch", "processor", "optimization"]
    },
    ...
  ],
  "total": 10
}
```

---

## Data Pipeline: From Upload to Vector DB

### Step-by-Step Processing

```
1. UPLOAD RECEIVED
   File: deployment-guide.pdf (5 MB)
   ↓

2. VALIDATE
   - File size < 100 MB ✓
   - Format supported (PDF) ✓
   - Scan for viruses (optional) ✓
   ↓

3. PARSE CONTENT
   Library: PyPDF2 (extract text from PDF)
   Output:
     raw_text = "Chapter 1: Introduction\n..."
     metadata = {title: "Deployment Guide", pages: 42}
   ↓

4. SPLIT INTO CHUNKS
   Strategy: 512 token chunks, 50 token overlap
   
   Example output:
     chunk_001: "Chapter 1: Introduction\nDeployment is..."
     chunk_002: "...is the process of taking code and..."
     chunk_003: "...running it in production. Key steps..."
   ↓

5. GENERATE EMBEDDINGS
   Model: all-MiniLM-L6-v2 (384 dimensions)
   Batching: Process 32 chunks at a time
   
   chunk_001 → [0.123, 0.456, ..., 0.789] (384 values)
   chunk_002 → [0.234, 0.567, ..., 0.890]
   ↓

6. CALCULATE QUALITY SCORE
   Formula:
     quality = (
       source_reliability * 0.4 +    # 1.0 for uploaded doc
       content_completeness * 0.2 +  # Based on chunk count
       recency_factor * 0.2 +        # Recent uploads scored higher
       language_confidence * 0.2     # English = 1.0
     )
   
   Result: Each chunk gets 0.0-1.0 score
   ↓

7. DEDUPLICATION
   - Compare embeddings: if similarity > 0.95, it's duplicate
   - Keep original, mark new as duplicate
   - Store both IDs but only one vector
   ↓

8. ADD TO QDRANT
   Payload sent to Qdrant:
   {
     "id": "kb_20260519_001",
     "vector": [0.123, 0.456, ..., 0.789],
     "payload": {
       "content": "Chapter 1: Introduction...",
       "source_type": "api:upload",
       "quality_score": 0.85,
       "document_id": "doc_xyz",
       "chunk_index": 0,
       "tags": ["deployment", "guide"]
     }
   }
   ↓

9. INDEX IN POSTGRES
   INSERT INTO knowledge_base (
     id, original_document_id, chunk_index, content,
     embedding, source_type, quality_score, status
   ) VALUES (...)
   ↓

10. WEBHOOK NOTIFICATION (Optional)
    POST https://team-platform/webhooks/knowledge-imported
    {
      "import_job_id": "job_20260519_abc",
      "status": "complete",
      "chunks_created": 47,
      "quality_scores": {
        "min": 0.78,
        "max": 0.95,
        "avg": 0.88
      }
    }
    ↓

✅ COMPLETE - Knowledge ready for search & pattern mining
```

---

## Lightweight Implementation: Tech Stack

### Recommended Stack (Production-Ready)

```yaml
API Framework:
  - FastAPI (Python)
  - Pydantic (validation)
  - python-multipart (file uploads)

Document Parsing:
  - PyPDF2 (PDF)
  - python-docx (DOCX)
  - pandoc (universal converter)
  - csv/json (built-in)

Chunking & Embedding:
  - LangChain (splitting strategies)
  - sentence-transformers (embeddings)
  - scikit-learn (deduplication via cosine similarity)

Vector Storage:
  - Qdrant (local Docker or cloud)
  - Connection pooling: asyncpg

Database:
  - PostgreSQL (metadata + lineage)
  - Redis (import job queue)

Job Processing:
  - Celery (async import jobs)
  - Redis (Celery broker)

Monitoring:
  - Langfuse (token usage, latency)
  - Custom metrics (import success rate, dedup %age)
```

### Docker Compose for Phase 0

```yaml
version: '3.8'

services:
  # PostgreSQL
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: platform
      POSTGRES_PASSWORD: password
      POSTGRES_DB: platform_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  # Qdrant vector DB
  qdrant:
    image: qdrant/qdrant:latest
    volumes:
      - qdrant_data:/qdrant/storage
    ports:
      - "6333:6333"  # HTTP API
      - "6334:6334"  # gRPC

  # Redis for Celery
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  # FastAPI backend
  api:
    build: ./backend
    environment:
      DATABASE_URL: postgresql://platform:password@postgres:5432/platform_db
      QDRANT_URL: http://qdrant:6333
      REDIS_URL: redis://redis:6379
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - qdrant
      - redis

  # Celery worker
  celery:
    build: ./backend
    command: celery -A app worker --loglevel=info
    environment:
      DATABASE_URL: postgresql://platform:password@postgres:5432/platform_db
      QDRANT_URL: http://qdrant:6333
      REDIS_URL: redis://redis:6379
    depends_on:
      - postgres
      - qdrant
      - redis

volumes:
  postgres_data:
  qdrant_data:
```

---

## Implementation: Code Examples

### FastAPI Document Upload Handler

```python
# backend/api/knowledge/upload.py
from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, Depends
from sqlmodel import Session, select
import asyncio
import uuid
from datetime import datetime

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

async def process_document(
    file_path: str,
    user_id: str,
    tags: List[str],
    session: Session
):
    """
    Background task: Parse, chunk, embed, and store document.
    Called by Celery worker.
    """
    
    try:
        # 1. Parse document
        from langchain.document_loaders import PyPDFLoader, Docx2docLoader
        
        if file_path.endswith('.pdf'):
            loader = PyPDFLoader(file_path)
        elif file_path.endswith('.docx'):
            loader = Docx2docLoader(file_path)
        else:
            raise ValueError(f"Unsupported format")
        
        docs = loader.load()
        
        # 2. Split into chunks
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=512,
            chunk_overlap=50,
            separators=["\n\n", "\n", " ", ""]
        )
        
        chunks = splitter.split_documents(docs)
        
        # 3. Generate embeddings
        from sentence_transformers import SentenceTransformer
        
        model = SentenceTransformer('all-MiniLM-L6-v2')
        embeddings = model.encode(
            [chunk.page_content for chunk in chunks],
            batch_size=32,
            convert_to_tensor=False
        )
        
        # 4. Check for duplicates
        existing_embeddings = session.exec(
            select(KnowledgeBase.embedding)
            .where(KnowledgeBase.embedding != None)
        ).all()
        
        duplicates = []
        if existing_embeddings:
            from sklearn.metrics.pairwise import cosine_similarity
            for i, embedding in enumerate(embeddings):
                scores = cosine_similarity([embedding], existing_embeddings)[0]
                if scores.max() > 0.95:
                    duplicates.append(i)
        
        # 5. Store in database + Qdrant
        from qdrant_client import QdrantClient
        
        qdrant = QdrantClient(url="http://localhost:6333")
        
        source_doc = SourceDocument(
            user_id=user_id,
            filename=file_path.split('/')[-1],
            file_format=file_path.split('.')[-1],
            status="processing"
        )
        session.add(source_doc)
        session.flush()
        
        quality_scores = []
        kb_entries = []
        
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            if i in duplicates:
                continue
            
            # Calculate quality score
            quality = (
                1.0 * 0.4 +  # Uploaded doc = high reliability
                min(1.0, len(chunks) / 100) * 0.2 +  # Completeness
                1.0 * 0.2 +  # Recent = high
                1.0 * 0.2    # Language confidence
            )
            
            quality_scores.append(quality)
            
            kb_entry = KnowledgeBase(
                original_document_id=source_doc.id,
                chunk_index=i,
                content=chunk.page_content,
                chunk_length=len(chunk.page_content.split()),
                embedding=embedding.tolist(),
                embedding_model="all-MiniLM-L6-v2",
                source_type="api:upload",
                source_reference=source_doc.id,
                document_title=source_doc.filename,
                quality_score=quality,
                relevance_tags=tags or [],
                author=user_id,
                created_at=datetime.utcnow(),
                status="active"
            )
            
            session.add(kb_entry)
            kb_entries.append(kb_entry)
        
        session.commit()
        
        # Add to Qdrant
        points = [
            Point(
                id=int(kb.id),
                vector=kb.embedding,
                payload={
                    "content": kb.content,
                    "source": "api:upload",
                    "quality_score": kb.quality_score,
                    "tags": kb.relevance_tags
                }
            )
            for kb in kb_entries
        ]
        
        qdrant.upsert(
            collection_name="knowledge",
            points=points
        )
        
        # Update source document status
        source_doc.status = "complete"
        source_doc.chunks_created = len(chunks)
        source_doc.chunks_deduplicated = len(duplicates)
        source_doc.quality_scores = quality_scores
        session.add(source_doc)
        session.commit()
        
        return {
            "status": "complete",
            "chunks_created": len(chunks),
            "duplicates_found": len(duplicates)
        }
    
    except Exception as e:
        source_doc.status = "failed"
        source_doc.error_message = str(e)
        session.add(source_doc)
        session.commit()
        raise

@router.post("/upload")
async def upload_knowledge(
    file: UploadFile = File(...),
    title: str = Form(None),
    tags: str = Form(""),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    session: Session = Depends(get_session),
    user = Depends(get_user_from_key)
):
    """Upload single document for RAG ingestion."""
    
    # Save file temporarily
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    # Create source document record
    source_doc = SourceDocument(
        user_id=user.id,
        filename=file.filename,
        file_format=file.filename.split('.')[-1],
        status="processing",
        ingestion_method="api_upload"
    )
    session.add(source_doc)
    session.commit()
    
    # Queue background processing
    from app.tasks import process_document_task
    
    background_tasks.add_task(
        process_document_task,
        tmp_path,
        user.id,
        tags.split(","),
        str(source_doc.id)
    )
    
    return {
        "import_job_id": str(source_doc.id),
        "filename": file.filename,
        "status": "processing",
        "check_status_url": f"/api/v1/knowledge/import-status/{source_doc.id}"
    }

@router.get("/import-status/{import_job_id}")
async def check_import_status(
    import_job_id: str,
    session: Session = Depends(get_session)
):
    """Check status of import job."""
    
    source_doc = session.get(SourceDocument, import_job_id)
    if not source_doc:
        raise HTTPException(status_code=404, detail="Import job not found")
    
    return {
        "status": source_doc.status,
        "chunks_created": source_doc.chunks_created,
        "chunks_deduplicated": source_doc.chunks_deduplicated,
        "quality_scores": {
            "min": min(source_doc.quality_scores or [0]),
            "max": max(source_doc.quality_scores or [0]),
            "avg": sum(source_doc.quality_scores or [0]) / len(source_doc.quality_scores or [1])
        }
    }
```

---

## Comparison: Different RAG Approaches

### Option A: Build from Scratch (❌ NOT RECOMMENDED)
```
Effort: 3-4 months
Cost: High
Maintenance: High
Benefit: Complete control
Reality: Over-engineered for our use case
```

### Option B: Use RAG-Anything (✅ GOOD)
```
Effort: 2-3 weeks to integrate
Cost: Moderate
Maintenance: Moderate (depends on project maintenance)
Benefit: Multi-format support, well-designed
Trade-off: Heavier than we need
Reference: GitHub HKUDS/RAG-Anything
```

### Option C: Compose Best Libraries (✅ RECOMMENDED - LIGHTWEIGHT)
```
Stack:
  - LangChain (document loading + chunking)
  - sentence-transformers (embeddings)
  - Qdrant (vector DB)
  - FastAPI (API)
  - PostgreSQL (metadata)

Effort: 1-2 weeks to integrate
Cost: Low
Maintenance: Low (all popular, well-maintained projects)
Benefit: Lightweight, customizable, modular
Why: Perfect balance of simplicity + capability
```

### Option D: Use Managed RAG Service (❌ NOT FOR MVP)
```
Services: Pinecone, Weaviate Cloud, etc.
Effort: 1 week
Cost: High (per token, per search)
Lock-in: Vendor lock-in
When to use: After proving value in Phase 1
```

---

## Recommended Path: Lightweight + Scalable

### Phase 0 (Weeks 1-3): Foundation
```
✅ Keep it simple
- Single-machine Qdrant (Docker)
- PostgreSQL local
- Redis for job queue
- FastAPI upload API
- Celery workers for async processing

Capacity: 100K documents, 500K chunks easily
Development time: 1-2 weeks
```

### Phase 1 (Weeks 4-6): Scale & Optimize
```
Improvements:
- Batch import API (CSV, GitHub)
- Quality scoring refinement
- Hybrid search (semantic + BM25)
- Knowledge lineage tracking
- Automatic deduplication tuning

Still lightweight:
- Same stack
- Just more features on top
```

### Phase 2 (Weeks 7+): Scale & Distribute
```
If traffic justifies:
- Move Qdrant to managed instance (Qdrant Cloud)
- Horizontal Celery workers
- Elasticsearch for keyword search (hybrid)
- Caching layer (Redis for hot queries)

Cost: Still <$1000/month for infrastructure
```

---

## Data Lifecycle: From Upload to Archive

```
┌─────────────────────────────────────────┐
│           KNOWLEDGE LIFECYCLE           │
├─────────────────────────────────────────┤
│                                         │
│ 1. ACTIVE (0-30 days)                   │
│    └─ Quality score high (0.7-1.0)     │
│    └─ Searchable, usable                │
│    └─ In Qdrant + PostgreSQL            │
│    └─ Updated on access (access_count++) │
│                                         │
│ 2. AGING (30-90 days)                   │
│    └─ Score gradually decreased         │
│    └─ Still searchable                  │
│    └─ Keep if accessed regularly        │
│    └─ Archive if not accessed           │
│                                         │
│ 3. ARCHIVED (90+ days, no access)       │
│    └─ Moved to cold storage             │
│    └─ Not in Qdrant search              │
│    └─ Still accessible via query        │
│    └─ Can be restored if needed         │
│                                         │
│ 4. DELETED (on user request)            │
│    └─ Permanently removed               │
│    └─ No recovery                       │
│    └─ Audit logged                      │
│                                         │
└─────────────────────────────────────────┘

Automatic cleanup job (weekly):
  SELECT * FROM knowledge_base
  WHERE status = 'active'
    AND accessed_at IS NULL
    AND created_at < NOW() - INTERVAL 90 DAY
  
  Move to archived:
    UPDATE knowledge_base
    SET status = 'archived', archived_at = NOW()
    WHERE [above conditions]
    
  Remove from Qdrant:
    DELETE FROM qdrant collection WHERE kb_id IN (archived_ids)
```

---

## Quality Scoring: The Formula

```
Quality Score = (
  source_reliability * 0.40 +
  recency_factor * 0.20 +
  community_validation * 0.20 +
  specificity * 0.10 +
  freshness * 0.10
)

source_reliability:
  - Git commits (merged to main): 0.95
  - Uploaded by user: 0.80
  - Crawled from public docs: 0.70
  - Chat messages: 0.50

recency_factor:
  - Created today: 1.0
  - Created 7 days ago: 0.9
  - Created 30 days ago: 0.7
  - Created 90+ days ago: 0.4

community_validation:
  - If used in proposals: +0.1
  - If used in accepted skills: +0.15
  - If user rated positively: +0.1

specificity:
  - Code examples: 1.0
  - Detailed explanations: 0.9
  - General overview: 0.6
  - Speculation: 0.3

freshness (decay over time):
  - If accessed in last 7 days: 1.0
  - If accessed in last 30 days: 0.8
  - If never accessed: 0.5

Example scores:
  "Deployment guide" (user uploaded): 0.85
  "Git commit fix": 0.92
  "Old chat message": 0.45
  "Integration test code": 0.88
```

---

## Security & Privacy

### Access Control

```python
# Virtual Key scopes for RAG
read:knowledge        # Can search RAG
write:knowledge       # Can upload documents
admin:knowledge       # Can delete, archive
delete:knowledge      # Can permanently delete

# Each virtual key has specific scopes
vk_cli_dev:
  - read:knowledge (full search)
  - write:knowledge (can upload)
  - ✗ delete:knowledge (destructive)

vk_bot:
  - read:knowledge (full search)
  - ✗ write:knowledge (no uploads)
  - ✗ delete:knowledge
```

### Data Privacy

```
Sensitive data handling:
  - No PII in knowledge base
  - No credentials/secrets
  - Pre-processing: Strip email, phone from uploads
  - Audit logs: Who accessed what, when

GDPR compliance:
  - Right to deletion: Can delete personal doc
  - Data export: Can export all my uploads
  - Retention: Auto-delete after 1 year if inactive
```

---

## Success Metrics

### By Week 3 (Phase 0)
```
✅ Document upload working
   - 50+ documents uploaded via API
   - Average processing time: <1 minute
   
✅ RAG search accurate
   - Top-1 relevance score: >0.8 for common queries
   - Search latency: <200ms
   
✅ Deduplication effective
   - False positive rate: <5%
   - True positive rate: >95%
```

### By Week 6 (Phase 1)
```
✅ Knowledge base useful
   - 500+ total knowledge entries
   - Search used 50+ times by team
   
✅ Quality scores meaningful
   - High-quality knowledge (>0.8) used more
   - Low-quality knowledge (<0.5) rarely used
   
✅ Batch import working
   - Import 100 documents in <5 minutes
```

---

## Next Steps

1. **Choose tech stack** (confirm LangChain + Qdrant + PostgreSQL)
2. **Set up Docker Compose** (local dev environment)
3. **Implement upload API** (single file + batch)
4. **Start document ingestion** (manual imports to seed knowledge)
5. **Integrate Git hooks** (passive collection starts)
6. **Build search UI** (show knowledge in dashboard)

This approach gives you a **lightweight, scalable, maintainable RAG system** without the overhead of building from scratch.

**Total effort: 2-3 weeks for Phase 0 implementation.**
