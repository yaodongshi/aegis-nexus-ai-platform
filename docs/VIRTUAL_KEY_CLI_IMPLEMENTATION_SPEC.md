# 🔑 Virtual Key & CLI Implementation Specification

**Purpose:** Define technical implementation of Virtual Key system and CLI tool  
**Scope:** Authentication, authorization, API contracts, CLI commands  
**Status:** Complete Specification v1.0  
**Date:** 2026-05-19

---

## Table of Contents

1. [Virtual Key Data Model & Lifecycle](#virtual-key-data-model--lifecycle)
2. [Virtual Key Authentication Flow](#virtual-key-authentication-flow)
3. [Permission & Scope System](#permission--scope-system)
4. [CLI Command Reference](#cli-command-reference)
5. [API Contracts](#api-contracts)
6. [Integration Examples](#integration-examples)
7. [Security Considerations](#security-considerations)
8. [Testing Strategy](#testing-strategy)

---

## Virtual Key Data Model & Lifecycle

### Virtual Key Database Schema

```sql
-- Virtual Key Storage
CREATE TABLE virtual_keys (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  name VARCHAR(255) NOT NULL,
  
  -- Key Material
  key_secret_hash VARCHAR(255) NOT NULL,  -- PBKDF2-HMAC-SHA256 hash
  key_public_prefix VARCHAR(10) NOT NULL,  -- First 10 chars of key (for display)
  
  -- Permissions & Rate Limiting
  scopes JSONB NOT NULL,  -- {"read:skills": true, "write:skills": true, ...}
  rate_limit_requests INT NOT NULL DEFAULT 1000,  -- per hour
  rate_limit_tokens INT NOT NULL DEFAULT 100000,  -- for LLM calls
  
  -- Lifecycle
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMP,  -- NULL = never expires
  last_used_at TIMESTAMP,
  last_used_ip VARCHAR(45),  -- IPv4 or IPv6
  
  -- Status
  status VARCHAR(20) NOT NULL DEFAULT 'active',  -- active | deprecated | revoked
  revoked_at TIMESTAMP,
  revoked_reason VARCHAR(255),
  
  -- Metadata
  description VARCHAR(500),
  created_from_ip VARCHAR(45),
  
  UNIQUE(user_id, name),
  INDEX idx_user_keys (user_id),
  INDEX idx_key_prefix (key_public_prefix),
  INDEX idx_status (status),
  INDEX idx_expires (expires_at)
);

-- Virtual Key Usage Audit Log
CREATE TABLE virtual_key_audit_logs (
  id BIGSERIAL PRIMARY KEY,
  virtual_key_id UUID NOT NULL REFERENCES virtual_keys(id),
  user_id UUID NOT NULL REFERENCES users(id),
  
  -- Request Details
  method VARCHAR(10) NOT NULL,  -- GET, POST, PUT, DELETE
  endpoint VARCHAR(255) NOT NULL,
  status_code INT NOT NULL,
  
  -- Auth Details
  success BOOLEAN NOT NULL,  -- true = authenticated, false = failed
  failure_reason VARCHAR(255),  -- rate limit | invalid key | expired | permission denied
  
  -- Telemetry
  request_size INT,  -- bytes
  response_size INT,  -- bytes
  latency_ms INT,
  
  -- Context
  ip_address VARCHAR(45),
  user_agent VARCHAR(500),
  timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
  
  INDEX idx_virtual_key_id (virtual_key_id),
  INDEX idx_user_id (user_id),
  INDEX idx_timestamp (timestamp),
  INDEX idx_status_code (status_code)
);

-- Virtual Key Permission Definitions
CREATE TABLE virtual_key_permissions (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100) UNIQUE NOT NULL,
  description VARCHAR(255),
  category VARCHAR(50),  -- read | write | execute | admin
  risk_level VARCHAR(20),  -- low | medium | high | critical
  
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Insert standard permissions
INSERT INTO virtual_key_permissions (name, category, risk_level, description) VALUES
  ('read:skills', 'read', 'low', 'Read skill definitions'),
  ('write:skills', 'write', 'high', 'Create/edit skills'),
  ('publish:skills', 'write', 'critical', 'Publish skills (immutable)'),
  ('delete:skills', 'write', 'critical', 'Delete skills'),
  ('execute:agent', 'execute', 'high', 'Run agents'),
  ('read:knowledge', 'read', 'low', 'Search knowledge base'),
  ('write:knowledge', 'write', 'medium', 'Ingest knowledge'),
  ('read:proposals', 'read', 'low', 'View skill proposals'),
  ('admin:users', 'admin', 'critical', 'User management'),
  ('admin:keys', 'admin', 'critical', 'Virtual key management');
```

### Virtual Key Lifecycle

```
┌─────────────────────────────────────────────────────┐
│                  VIRTUAL KEY LIFECYCLE              │
└─────────────────────────────────────────────────────┘

1️⃣ CREATION
   User runs: team key create --name dev
   ↓
   CLI calls: POST /api/v1/keys
   ↓
   Server:
   - Generates random 32-byte key
   - Hashes with PBKDF2-HMAC-SHA256 (100k iterations)
   - Stores hash in DB (secret not stored)
   - Returns key once (never retrievable again)
   
   Response: vk_20260519_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
   
2️⃣ ACTIVE USE
   User includes key in API requests:
   Authorization: Bearer vk_20260519_...
   ↓
   Every request:
   - Verify key exists + not revoked
   - Verify not expired
   - Verify rate limit not exceeded
   - Check permissions
   - Log request to audit_logs
   - Update last_used_at + last_used_ip

3️⃣ ROTATION (Optional, Recommended Every 90 Days)
   User runs: team key rotate dev
   ↓
   Server:
   - Generates new key
   - Marks old key as "deprecated" (still works for 7 days)
   - Returns new key
   - User updates config to use new key
   - After 7 days, old key revoked automatically

4️⃣ REVOCATION (Immediate & Permanent)
   User runs: team key revoke dev
   ↓
   OR automatic on:
   - Expiration date reached
   - Rate limit abuse detected
   - Security incident
   ↓
   Server:
   - Sets status = 'revoked'
   - Sets revoked_at = NOW()
   - All future requests with this key → 401 Unauthorized
   - Cannot be undone (must create new key)

5️⃣ EXPIRATION (Automatic)
   If expires_at is set and current_time > expires_at:
   ↓
   Server:
   - Treats key as revoked
   - Returns: 401 Unauthorized (key expired)
   - User must create new key OR rotate
   - No automatic renewal (intentional)
```

### Virtual Key Types & Use Cases

```yaml
Type 1: Developer Local Key
  Name: vk_cli_dev
  Scopes: [read:skills, write:skills (draft only), execute:agent:test]
  Rate limit: 1000/hour (personal)
  Expires: 90 days
  Usage: Local development, testing
  Location: ~/.team/config.json (encrypted)

Type 2: CI/CD Pipeline Key
  Name: vk_ci_deploy
  Scopes: [read:skills, execute:agent:deploy, write:skills (published)]
  Rate limit: 100/hour (limited, production sensitive)
  Expires: 365 days (needs to be stable)
  Usage: GitHub Actions, Jenkins, automated deployments
  Location: GitHub Secrets, CI/CD environment
  Rotation: Quarterly

Type 3: Bot/Integration Key
  Name: vk_slack_bot
  Scopes: [read:skills, read:knowledge, create:proposal:link]
  Rate limit: 10000/hour (high traffic from bot)
  Expires: null (no expiration for always-on services)
  Usage: Slack bot, webhooks, third-party integrations
  Location: Service environment variables
  Rotation: On-demand (if compromised)

Type 4: Temporary/Contractor Key
  Name: vk_contractor_review_pr
  Scopes: [read:skills, read:knowledge, read:proposals]
  Rate limit: 100/hour
  Expires: 2026-06-01 (specific end date)
  Usage: Contractor reviewing code for limited time
  Location: Email or secure handoff
  Notes: Auto-revokes at expiration

Type 5: Service Account Key
  Name: vk_monitoring_agent
  Scopes: [read:metrics, write:alerts, execute:agent:monitor]
  Rate limit: 5000/hour
  Expires: null
  Usage: Internal monitoring system
  Location: Monitoring service config
  Notes: System account, not human user
```

---

## Virtual Key Authentication Flow

### OAuth-Style CLI Authentication (First Time)

```
Step 1: User initiates login
┌─────────────┐
│ User's Mac  │
│             │
│ $ team login│
└──────┬──────┘
       │
       │ Opens browser
       ↓
┌──────────────────────────────────┐
│ Browser → https://platform/...   │
│ /auth/cli-login                  │
└──────┬───────────────────────────┘
       │
       ↓
Step 2: Platform generates auth code
┌────────────────────────────────────────────┐
│ Platform Backend                           │
│                                            │
│ 1. Generate random auth_code (32 bytes)   │
│ 2. Store in Redis: auth_code → {          │
│      user_id: <pending>,                  │
│      created_at: NOW(),                   │
│      expires_at: NOW() + 10 min,          │
│      redeemed: false                      │
│    }                                       │
│ 3. Display auth_code on screen            │
└────────┬───────────────────────────────────┘
         │
Step 3: User copies code or clicks "Confirm"
┌──────────────────────────────┐
│ Browser (authenticated)       │
│                              │
│ [✓ Confirm login for CLI]   │
│ Code: ABC123DEF456           │
│ (Expires in 5 minutes)       │
└──────┬───────────────────────┘
       │ Clicks [Confirm]
       │
       ↓
Step 4: CLI polls for confirmation
┌─────────────────────────────┐
│ CLI on user's Mac           │
│ (waiting in background)     │
│                             │
│ Poll: GET /auth/cli-status  │
│       ?code=ABC123DEF456    │
│       (every 2 seconds)     │
└─────────┬───────────────────┘
          │
          │ (user clicks Confirm)
          │
          ↓
Step 5: Platform confirms & creates virtual key
┌──────────────────────────────────────┐
│ Platform Backend                     │
│                                      │
│ 1. Verify auth_code not expired      │
│ 2. Verify user_id associated         │
│ 3. Set redeemed = true               │
│ 4. Create new virtual key:           │
│    {                                 │
│      user_id: alice@company.com     │
│      name: "cli-dev"                │
│      key: vk_20260519_xxxxx         │
│      scopes: {read, write draft}    │
│      expires_at: +90 days           │
│    }                                 │
│ 5. Return key one-time              │
└──────┬───────────────────────────────┘
       │
       ↓
Step 6: CLI stores key (encrypted)
┌──────────────────────────────────────┐
│ CLI on user's Mac                    │
│                                      │
│ Receive: vk_20260519_xxxxx          │
│ Save to: ~/.team/config.json         │
│ Encrypt: Using system keyring        │
│ Set permissions: 600 (user only)    │
│                                      │
│ ✓ Setup complete!                   │
│ You're logged in.                    │
└──────────────────────────────────────┘

Key Points:
✓ User never enters password on CLI (uses browser login)
✓ Code is single-use (one confirmation = one virtual key)
✓ Key expires in 10 minutes if not confirmed
✓ Key returned only once (can't retrieve later)
✓ Key stored encrypted locally (not in plain text)
```

### Subsequent API Requests Using Virtual Key

```
Request Flow:

1️⃣ User makes CLI request
   $ team skill list
   
2️⃣ CLI reads virtual key from config
   ~/.team/config.json:
   {
     "active_key": "cli-dev",
     "keys": {
       "cli-dev": {
         "secret": "vk_20260519_xxxxx",  // encrypted in keyring
         "scopes": ["read:skills", "write:skills"],
         "created_at": "2026-05-19"
       }
     }
   }

3️⃣ CLI makes HTTP request
   GET /api/v1/skills
   Authorization: Bearer vk_20260519_xxxxx
   User-Agent: team-cli/1.0.0
   X-Request-ID: req_20260519_abc123

4️⃣ Server validates key
   a) Extract key from header: vk_20260519_xxxxx
   b) Query DB: SELECT * FROM virtual_keys WHERE key_secret_hash = hash(key)
   c) Verify:
      - Key exists ✓
      - status = 'active' ✓
      - expires_at IS NULL or expires_at > NOW() ✓
      - rate limit not exceeded ✓
      - scopes include 'read:skills' ✓
   
5️⃣ If all checks pass:
   - Execute request
   - Update virtual_keys.last_used_at = NOW()
   - Update virtual_keys.last_used_ip = request.ip
   - Log to virtual_key_audit_logs
   - Return response

6️⃣ If any check fails:
   - Log audit entry with failure_reason
   - Return 401 Unauthorized
   - Examples:
     • "rate limit exceeded" (1000+ requests/hour)
     • "key expired" (expires_at < NOW())
     • "insufficient permissions" (scopes don't include 'read:skills')
     • "key revoked" (status = 'revoked')
```

---

## Permission & Scope System

### Permission Categories

```yaml
READ Permissions (lowest risk):
  - read:skills           # View skill definitions
  - read:knowledge        # Search knowledge base
  - read:proposals        # View skill proposals
  - read:agents           # View agent definitions
  - read:metrics          # View execution metrics

WRITE Permissions (higher risk):
  - write:skills          # Create/edit skills (draft only)
  - write:knowledge       # Ingest knowledge base
  - create:suggestions    # Create improvement suggestions

PUBLISH Permissions (critical):
  - publish:skills        # Publish skill (immutable version)
  - approve:proposals     # Approve AI-generated proposals

EXECUTE Permissions (high risk):
  - execute:agent         # Run any agent
  - execute:agent:deploy  # Run deployment agents only
  - execute:agent:test    # Run test agents only

ADMIN Permissions (critical):
  - admin:keys            # Manage own/team virtual keys
  - admin:users           # User management
  - admin:policies        # Modify rate limits/permissions
  - admin:audit           # View audit logs
```

### Scope Resolution Examples

```yaml
Example 1: Developer
  Key: vk_cli_dev
  Requested scopes: [read:skills, write:skills]
  Applied scopes: [read:skills, write:skills (draft only)]
  Rationale: Can develop skills but can't publish
  Permissions: ✓ create draft, ✓ edit draft, ✓ read published, ✗ publish
  
Example 2: CI/CD
  Key: vk_ci_deploy
  Requested scopes: [read:skills, execute:agent, publish:skills]
  Applied scopes: [read:skills, execute:agent:deploy, publish:skills]
  Rationale: Deployment requires publishing but limited agent execution
  Permissions: ✓ read, ✓ run deploy agents, ✓ publish, ✗ run test agents
  
Example 3: Slack Bot
  Key: vk_slack_bot
  Requested scopes: [read:skills, read:knowledge, create:suggestions]
  Applied scopes: [read:skills, read:knowledge, create:proposals:link]
  Rationale: Read-only + ability to link to proposals
  Permissions: ✓ search, ✓ view proposals, ✗ create new proposals, ✗ execute

Example 4: Contractor (Temporary)
  Key: vk_contractor_review
  Requested scopes: [read:skills, read:proposals]
  Applied scopes: [read:skills (public), read:proposals]
  Rationale: Limited to review only, expires 2026-06-01
  Permissions: ✓ view public skills, ✓ view proposals, ✗ edit, ✗ publish
  Expiration: Auto-revoked on 2026-06-01
```

### Rate Limiting with Virtual Keys

```
Rate Limit Enforcement:

Type 1: Per-Key Rate Limiting
┌─────────────────────────────────┐
│ Virtual Key: vk_cli_dev         │
│ Rate limit: 1000 req/hour       │
│                                 │
│ Token bucket algorithm:         │
│ - Capacity: 1000 tokens         │
│ - Refill rate: 1000 tokens/hour │
│ - Each request: -1 token        │
│                                 │
│ User hits 1000 requests in 30min│
│ ↓ bucket empty                  │
│ ↓ next request → 429 Too Many   │
│ ↓ "retry after 30 minutes"      │
│                                 │
│ Error response:                 │
│ HTTP 429 Too Many Requests      │
│ Retry-After: 1800 (seconds)     │
│ X-RateLimit-Limit: 1000         │
│ X-RateLimit-Remaining: 0        │
│ X-RateLimit-Reset: 1000000000   │
└─────────────────────────────────┘

Type 2: Separate Token Budget
Some scopes have additional budget:
  - execute:agent → 100 token executions/hour
    (each LLM call = multiple tokens)
  - write:knowledge → 50 GB ingestion/month
  
User hits token budget:
  ↓ even if request count OK
  ↓ request → 429 Too Many Requests
  ↓ reason: "token budget exceeded"

Type 3: Dynamic Rate Limiting
Anomaly detection:
  - Sudden spike in requests → rate limit reduced temporarily
  - Repeated 429 errors → investigate (possible leak)
  - Unusual IP accessing key → alert user
  
Example:
  Key normally: 10 requests/minute
  Sudden spike: 1000 requests/minute from unknown IP
  ↓ Rate limit reduced to 5 requests/minute temporarily
  ↓ Alert sent to user: "Unusual activity detected"
  ↓ User can investigate + rotate key if needed
```

---

## CLI Command Reference

### Installation & Setup

```bash
# Install CLI (npm)
npm install -g @team/platform-cli

# Verify installation
team --version
# team/1.0.0

# First-time setup
team login
# Opens browser → authenticate → confirm → saves virtual key

# Check who you are
team whoami
# User: alice@company.com
# Active key: cli-dev
# Created: 2026-05-01
# Scopes: read:skills, write:skills, execute:agent:test
```

### Skill Commands

```bash
# List skills
team skill list
team skill list --filter "tag1,tag2"
team skill list --format json
team skill list --state "draft|published|deprecated|archived"

# Create new skill
team skill create
# Interactive wizard: name, description, type, etc.

team skill create --file skill.yaml
# From YAML file (see schema below)

# Get skill details
team skill get <skill-id>
team skill get <skill-id> --format json
team skill get <skill-id> --include versions

# Edit skill (draft only)
team skill edit <skill-id>
# Opens $EDITOR with current skill content

team skill update <skill-id> --file skill.yaml
# Replace entire skill

# Publish skill (makes immutable)
team skill publish <skill-id>
# Creates version + triggers approval gates

# Rollback to previous version
team skill rollback <skill-id> --to-version 1.0.0
# Creates new draft version, doesn't revert

# Deprecate skill (still usable, not for new uses)
team skill deprecate <skill-id>

# Archive skill (removed from active list)
team skill archive <skill-id>

# Push local changes to platform
team skill push [<skill-id>]
# Batch update

# Pull skill from platform
team skill pull <skill-id>
# Download for local editing
```

### Skill YAML Format

```yaml
# skill.yaml
name: Auto-Deploy with Checklist
description: Automated deployment with pre-flight checks
version: 1.0.0-draft
author: alice@company.com

type: workflow  # workflow | code_template | documentation | query_template

tags:
  - deployment
  - automation
  - devops

scopes:
  - execute:agent:deploy  # Required permissions to use this skill

# For workflow type
workflow:
  steps:
    - name: Validate commit
      action: verify-commit-hash
      input: commit_hash
    
    - name: Run migrations
      action: database-migrate
      input: target_env
    
    - name: Deploy service
      action: kubernetes-deploy
      input:
        service: api
        environment: target_env
        commit: commit_hash

# For code template type
code_template:
  language: python
  framework: fastapi
  template: |
    async def process_batch(items: List[str]):
      """Resilient batch processor with exponential backoff."""
      ...

# For documentation type
documentation:
  format: markdown
  content: |
    # Troubleshooting Guide
    ...

# Test cases
tests:
  - name: "Happy path deployment"
    input:
      service: api
      env: staging
      commit: abc123
    expected_output:
      status: success
      checks_passed: 5

  - name: "Invalid environment"
    input:
      service: api
      env: invalid_env
      commit: abc123
    expected_output:
      status: failed
      reason: "invalid environment"

# Metadata
approval_gate: manual  # auto | manual
confidence_threshold: 0.85
estimated_impact:
  time_saved_minutes: 15
  error_reduction_percent: 30

linked_knowledge:
  - kb_20260515_incident_analysis
  - kb_20260510_deployment_guide
```

### Agent Commands

```bash
# List agents
team agent list
team agent list --filter active
team agent list --format table

# Get agent details
team agent get <agent-id>

# Run agent (on-demand)
team agent run <agent-id>
# Interactive prompts for required inputs

team agent run <agent-id> --input input.json
# Non-interactive with input file

team agent run <agent-id> --input '{"key": "value"}'
# Inline JSON input

team agent run <agent-id> --timeout 300
# Custom timeout (seconds)

# View agent logs
team agent logs <agent-id>
team agent logs <agent-id> --tail 50
# View recent log entries

# View execution history
team agent history <agent-id>
team agent history <agent-id> --limit 10
# List recent executions with status
```

### Knowledge Commands

```bash
# Search knowledge
team knowledge search "batch processor"
team knowledge search "batch processor" --limit 20
team knowledge search "batch processor" --filter "tag:deployment"

# View knowledge entry
team knowledge get <knowledge-id>

# Ingest knowledge (manual)
team knowledge ingest --file document.md
team knowledge ingest --file document.md --tags "tag1,tag2"

# View knowledge linked to skill
team knowledge links <skill-id>
# Shows which knowledge influenced this skill
```

### Virtual Key Commands

```bash
# Create virtual key
team key create --name dev
team key create --name deploy --scopes "read:skills,execute:agent"
team key create --name temp --expires "2026-06-01"

# List virtual keys
team key list
team key list --format json

# Get key details
team key get <key-id>

# Rotate key (create new, keep old for 7 days)
team key rotate <key-id>

# Revoke key (immediate, permanent)
team key revoke <key-id>

# View key audit log
team key audit <key-id>
team key audit <key-id> --days 7
# Show recent access using this key
```

### Configuration Commands

```bash
# Set config
team config set active-key dev
team config set output-format json
team config set editor vim

# Get config
team config get active-key
team config get output-format

# View all config
team config list

# Reset config to defaults
team config reset
```

---

## API Contracts

### Authentication Endpoint

```
POST /api/v1/auth/cli-login
Create new auth code for CLI login

Request:
  (no body)

Response (200 OK):
{
  "auth_code": "ABC123DEF456",
  "expires_at": "2026-05-19T16:10:00Z",
  "verify_url": "https://platform/auth/confirm?code=ABC123DEF456"
}

Errors:
  429 Too Many Requests: Rate limited
```

### Check Auth Status Endpoint

```
GET /api/v1/auth/cli-status?code=ABC123DEF456
Poll to check if user confirmed login

Request:
  (no body)

Response (200 OK, pending):
{
  "status": "pending",
  "expires_in_seconds": 300
}

Response (200 OK, confirmed):
{
  "status": "confirmed",
  "virtual_key": "vk_20260519_xxxxx",
  "scopes": ["read:skills", "write:skills"],
  "created_at": "2026-05-19T16:05:00Z",
  "expires_at": "2026-08-19T16:05:00Z"
}

Response (200 OK, expired):
{
  "status": "expired"
}
```

### Virtual Key Management Endpoints

```
GET /api/v1/keys
List user's virtual keys

Auth: Bearer <virtual_key>
Response (200 OK):
[
  {
    "id": "key_12345",
    "name": "cli-dev",
    "key_prefix": "vk_20260519",
    "scopes": ["read:skills", "write:skills"],
    "created_at": "2026-05-01",
    "expires_at": "2026-08-01",
    "last_used_at": "2026-05-19T14:30:00Z",
    "status": "active"
  },
  {...}
]

POST /api/v1/keys
Create new virtual key

Auth: Bearer <virtual_key>
Request:
{
  "name": "ci-deploy",
  "scopes": ["read:skills", "execute:agent"],
  "expires_at": "2026-12-31T23:59:59Z",  // optional
  "rate_limit_requests": 500
}

Response (201 Created):
{
  "id": "key_new123",
  "key": "vk_20260519_newikey",  // Returned once only
  "scopes": ["read:skills", "execute:agent:deploy"],
  "created_at": "2026-05-19T16:00:00Z"
}

DELETE /api/v1/keys/<key-id>
Revoke virtual key

Auth: Bearer <virtual_key>
Response (204 No Content)
```

### Rate Limit Response Headers

All API responses include rate limit information:

```
HTTP/1.1 200 OK
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 987
X-RateLimit-Reset: 1747660800
X-RateLimit-Tokens-Limit: 100000
X-RateLimit-Tokens-Remaining: 99500
X-Request-ID: req_20260519_abc123

[Response body...]
```

### Rate Limited Response

```
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1747660800
Retry-After: 1800

{
  "error": "rate_limit_exceeded",
  "message": "Request limit exceeded: 1000 requests per hour",
  "retry_after_seconds": 1800,
  "reset_at": "2026-05-19T16:30:00Z"
}
```

---

## Integration Examples

### Example 1: Git Hooks Auto-Ingestion

```bash
#!/bin/bash
# File: .git/hooks/post-commit
# Auto-installed when user runs: team init

set -e

# Get config
CONFIG_FILE="${HOME}/.team/config.json"
if [ ! -f "$CONFIG_FILE" ]; then
  exit 0  # Not configured, skip
fi

# Read virtual key from keychain (macOS example)
VK=$(security find-generic-password -w -l "team-cli-key" 2>/dev/null || echo "")
if [ -z "$VK" ]; then
  exit 0  # No key, skip
fi

# Get commit info
COMMIT_HASH=$(git rev-parse HEAD)
COMMIT_MSG=$(git log -1 --pretty=%B)
COMMIT_AUTHOR=$(git log -1 --pretty=%an)
COMMIT_DATE=$(git log -1 --pretty=%aI)

# Send to RAG (non-blocking, async)
nohup curl -s -X POST "https://platform/api/v1/knowledge/ingest" \
  -H "Authorization: Bearer $VK" \
  -H "Content-Type: application/json" \
  -d "{
    \"source\": \"git:commit\",
    \"repository\": \"core-platform\",
    \"hash\": \"$COMMIT_HASH\",
    \"message\": \"$COMMIT_MSG\",
    \"author\": \"$COMMIT_AUTHOR\",
    \"timestamp\": \"$COMMIT_DATE\",
    \"tags\": [\"code-change\", \"development\"]
  }" > /dev/null 2>&1 &

exit 0  # Always succeed (don't block commit)
```

### Example 2: GitHub Actions Deployment

```yaml
name: Deploy Service

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Configure Team CLI
        env:
          TEAM_VK: ${{ secrets.TEAM_VK_DEPLOY }}
        run: |
          npm install -g @team/platform-cli
          mkdir -p ~/.team
          echo "{\"virtual_key\": \"$TEAM_VK\"}" > ~/.team/config.json
          chmod 600 ~/.team/config.json
          team whoami

      - name: Deploy Service
        run: |
          team agent run deploy-service \
            --input '{
              "service": "api",
              "environment": "production",
              "commit": "${{ github.sha }}",
              "triggered_by": "github-actions"
            }'

      - name: Verify Deployment
        run: |
          team agent run health-check \
            --input '{"service": "api", "environment": "production"}'
```

### Example 3: Slack Bot Integration

```python
# slack_bot.py
import slack_bolt
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask
import requests
import os

app = Flask(__name__)

slack_app = slack_bolt.App(
    token=os.environ["SLACK_BOT_TOKEN"],
    signing_secret=os.environ["SLACK_SIGNING_SECRET"]
)

TEAM_VK = os.environ["TEAM_PLATFORM_VK"]
TEAM_API = "https://platform/api/v1"

# Handle: @team search <query>
@slack_app.message("search")
def handle_search(message, say, body):
    query = body["text"].replace("@team search ", "").strip()
    
    # Call Team Platform API
    response = requests.get(
        f"{TEAM_API}/knowledge/search",
        headers={"Authorization": f"Bearer {TEAM_VK}"},
        params={"query": query, "limit": 5}
    )
    
    results = response.json()
    
    # Format response
    blocks = [{
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"📚 Search results for: *{query}*"
        }
    }]
    
    for result in results:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"• {result['title']}\n{result['preview'][:200]}...\n<{result['url']}|View more>"
            }
        })
    
    say(blocks=blocks)

# Handle: @team run <agent>
@slack_app.message("run")
def handle_agent_run(message, say):
    agent_name = message["text"].replace("@team run ", "").strip()
    
    # Call Team Platform API
    response = requests.post(
        f"{TEAM_API}/agents/{agent_name}/execute",
        headers={"Authorization": f"Bearer {TEAM_VK}"},
        json={}
    )
    
    result = response.json()
    say(f"✓ Agent executed: {result['status']}")

handler = SlackRequestHandler(slack_app)

@app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

if __name__ == "__main__":
    app.run(port=3000)
```

---

## Security Considerations

### Secret Storage

```
❌ WRONG: Store key in plain text
  key.json: {"virtual_key": "vk_20260519_xxxxx"}
  
✓ CORRECT: Store in encrypted keyring
  macOS: Keychain (security add-generic-password)
  Linux: Pass or libsecret
  Windows: Credential Manager
  
CLI Implementation:
  import keyring
  
  # Store
  keyring.set_password("team-cli", "api-key", vk)
  
  # Retrieve
  vk = keyring.get_password("team-cli", "api-key")
```

### Key Rotation Best Practices

```
Recommended Schedule:
  - Developer keys: rotate every 30 days
  - CI/CD keys: rotate every 90 days
  - Bot keys: rotate on-demand (if compromised)
  - Service account keys: rotate quarterly
  
Automation:
  # Cron job: rotate dev key monthly
  0 0 1 * * team key rotate cli-dev
  
  # Alert: remind rotation due
  If (NOW() - last_rotated > 25 days) AND (expires_at - NOW() < 5 days):
    → Send email reminder to user
```

### Audit Trail

Every request is logged:

```
SELECT * FROM virtual_key_audit_logs
WHERE virtual_key_id = 'key_12345'
  AND timestamp > NOW() - INTERVAL 7 DAY
ORDER BY timestamp DESC
LIMIT 100;

Result:
  virtual_key_id | endpoint | method | status_code | success | timestamp
  ───────────────┼──────────┼────────┼─────────────┼─────────┼────────────
  key_12345 | /skills | GET | 200 | true | 2026-05-19 14:30:00
  key_12345 | /agents/deploy/run | POST | 200 | true | 2026-05-19 14:35:00
  key_12345 | /skills/abc/publish | POST | 403 | false | 2026-05-19 14:40:00
    (reason: insufficient permissions)
```

---

## Testing Strategy

### Unit Tests

```python
# tests/test_virtual_key.py

def test_virtual_key_creation():
    """VirtualKey can be created with name and scopes"""
    key = VirtualKey.create(
        user_id="user_123",
        name="test-key",
        scopes=["read:skills", "write:skills"]
    )
    
    assert key.status == "active"
    assert key.expires_at is None  # No expiration
    assert key.scopes == ["read:skills", "write:skills"]

def test_virtual_key_expiration():
    """VirtualKey expires at correct time"""
    key = VirtualKey.create(
        user_id="user_123",
        name="temp-key",
        expires_at=datetime.utcnow() + timedelta(days=1)
    )
    
    assert key.is_valid() == True
    
    # After expiration
    key.expires_at = datetime.utcnow() - timedelta(seconds=1)
    assert key.is_valid() == False

def test_virtual_key_rate_limiting():
    """VirtualKey rate limiting enforced"""
    key = VirtualKey.create(
        user_id="user_123",
        name="limited-key",
        rate_limit_requests=10
    )
    
    # Make 10 requests
    for i in range(10):
        assert key.check_rate_limit() == True
    
    # 11th request blocked
    assert key.check_rate_limit() == False
    
    # After reset
    key.reset_rate_limit()
    assert key.check_rate_limit() == True

def test_virtual_key_permission_check():
    """VirtualKey permission checking works"""
    key = VirtualKey.create(
        user_id="user_123",
        scopes=["read:skills"]  # No write permission
    )
    
    assert key.has_permission("read:skills") == True
    assert key.has_permission("write:skills") == False
```

### Integration Tests

```python
# tests/integration/test_cli_auth.py

def test_cli_login_flow():
    """Full CLI login flow"""
    # 1. Generate auth code
    auth_code = generate_auth_code()
    assert len(auth_code) == 32
    
    # 2. User confirms (simulate)
    confirm_login(auth_code, user_id="user_123")
    
    # 3. CLI polls for status
    status = get_auth_status(auth_code)
    assert status["status"] == "confirmed"
    assert "virtual_key" in status
    assert status["virtual_key"].startswith("vk_")
    
    # 4. Use virtual key
    response = requests.get(
        "https://platform/api/v1/skills",
        headers={"Authorization": f"Bearer {status['virtual_key']}"}
    )
    assert response.status_code == 200

def test_rate_limit_enforcement():
    """Rate limiting enforced on API"""
    key = create_virtual_key(rate_limit_requests=5)
    
    # Make 5 requests
    for i in range(5):
        response = requests.get(
            "https://platform/api/v1/skills",
            headers={"Authorization": f"Bearer {key}"}
        )
        assert response.status_code == 200
    
    # 6th request blocked
    response = requests.get(
        "https://platform/api/v1/skills",
        headers={"Authorization": f"Bearer {key}"}
    )
    assert response.status_code == 429
    assert response.json()["error"] == "rate_limit_exceeded"
```

---

## Implementation Checklist

- [ ] Virtual Key database schema (PostgreSQL)
- [ ] Key generation & hashing (PBKDF2-HMAC-SHA256)
- [ ] Rate limiting engine (token bucket algorithm)
- [ ] Permission validation system
- [ ] Audit logging system
- [ ] CLI tool (Node.js)
- [ ] Auth flow (OAuth-style browser login)
- [ ] API endpoints (all documented above)
- [ ] Keyring integration (macOS/Linux/Windows)
- [ ] Security tests (key leakage, rate limit bypass)
- [ ] Documentation (user guide, troubleshooting)
- [ ] Monitoring (key usage, rotation, anomalies)

---

## Next Steps

1. **Week 1-2:** Implement Virtual Key data model + API endpoints
2. **Week 3:** Build CLI tool + auth flow
3. **Week 4:** Integration tests + security audit
4. **Week 5:** Deploy + monitor for issues

**Success Criteria:**
- 100% of team using virtual keys (no personal tokens)
- <0.1% of keys compromised in first month
- CLI adoption >50% by Week 9
