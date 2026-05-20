#!/usr/bin/env bash
set -euo pipefail

# Vector store management helper for Team AI Platform.
# Provides create/manage/test operations against Qdrant + LiteLLM embeddings.

QDRANT_URL="${QDRANT_URL:-http://localhost:6333}"
LITELLM_BASE_URL="${LITELLM_BASE_URL:-http://localhost:4000}"
EMBEDDING_MODEL="${EMBEDDING_MODEL:-text-embedding-v3}"
LITELLM_MASTER_KEY="${LITELLM_MASTER_KEY:-}"
DEFAULT_VECTOR_SIZE="${VECTOR_SIZE:-1024}"
DEFAULT_DISTANCE="${VECTOR_DISTANCE:-Cosine}"

print_usage() {
  cat <<'EOF'
Usage:
  bash scripts/vector_store_management.sh create <collection> [vector_size] [distance]
  bash scripts/vector_store_management.sh list
  bash scripts/vector_store_management.sh stats <collection>
  bash scripts/vector_store_management.sh delete <collection>
  bash scripts/vector_store_management.sh upsert-text <collection> <point_id> <text> [payload_json]
  bash scripts/vector_store_management.sh search <collection> <query> [limit]
  bash scripts/vector_store_management.sh test <collection>

Environment:
  QDRANT_URL         default: http://localhost:6333
  LITELLM_BASE_URL   default: http://localhost:4000
  LITELLM_MASTER_KEY required for embedding operations
  EMBEDDING_MODEL    default: text-embedding-v3
  VECTOR_SIZE        default: 1024
  VECTOR_DISTANCE    default: Cosine

Examples:
  bash scripts/vector_store_management.sh create knowledge_base 1024 Cosine
  bash scripts/vector_store_management.sh upsert-text knowledge_base doc_1 "how to run e2e" '{"source":"manual"}'
  bash scripts/vector_store_management.sh search knowledge_base "how to run e2e" 5
  bash scripts/vector_store_management.sh test knowledge_base
EOF
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "[ERROR] Missing command: $1" >&2
    exit 1
  }
}

json_escape() {
  python3 - <<'PY' "$1"
import json, sys
print(json.dumps(sys.argv[1]))
PY
}

embed_text() {
  local text="$1"
  if [[ -z "${LITELLM_MASTER_KEY}" ]]; then
    echo "[ERROR] LITELLM_MASTER_KEY is required for embeddings." >&2
    exit 1
  fi

  local text_json
  text_json="$(json_escape "$text")"

  local resp
  resp="$(curl -fsS "${LITELLM_BASE_URL}/v1/embeddings" \
    -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
    -H 'Content-Type: application/json' \
    -d "{\"model\":\"${EMBEDDING_MODEL}\",\"input\":${text_json}}")"

  python3 - <<'PY' "$resp"
import json, sys
payload = json.loads(sys.argv[1])
vec = payload.get("data", [{}])[0].get("embedding")
if not isinstance(vec, list):
    raise SystemExit("invalid embedding response")
print(json.dumps(vec, separators=(",", ":")))
PY
}

create_collection() {
  local collection="$1"
  local size="${2:-$DEFAULT_VECTOR_SIZE}"
  local distance="${3:-$DEFAULT_DISTANCE}"

  echo "[INFO] Creating collection ${collection} (size=${size}, distance=${distance})"
  curl -fsS -X PUT "${QDRANT_URL}/collections/${collection}" \
    -H 'Content-Type: application/json' \
    -d "{\"vectors\":{\"size\":${size},\"distance\":\"${distance}\"}}" | cat
  echo
}

list_collections() {
  echo "[INFO] Listing vector stores from Qdrant"
  curl -fsS "${QDRANT_URL}/collections" | cat
  echo
}

collection_stats() {
  local collection="$1"
  echo "[INFO] Collection stats: ${collection}"
  curl -fsS "${QDRANT_URL}/collections/${collection}" | cat
  echo
}

delete_collection() {
  local collection="$1"
  echo "[WARN] Deleting collection ${collection}"
  curl -fsS -X DELETE "${QDRANT_URL}/collections/${collection}" | cat
  echo
}

upsert_text() {
  local collection="$1"
  local point_id="$2"
  local text="$3"
  local payload_json="${4:-{}}"

  local vector
  vector="$(embed_text "$text")"

  local text_json
  text_json="$(json_escape "$text")"

  local payload
  payload="$(python3 - <<'PY' "$payload_json" "$text_json"
import json, sys
base = json.loads(sys.argv[1]) if sys.argv[1].strip() else {}
base["text"] = json.loads(sys.argv[2])
print(json.dumps(base, separators=(",", ":")))
PY
)"

  echo "[INFO] Upserting point ${point_id} into ${collection}"
  curl -fsS -X PUT "${QDRANT_URL}/collections/${collection}/points?wait=true" \
    -H 'Content-Type: application/json' \
    -d "{\"points\":[{\"id\":\"${point_id}\",\"vector\":${vector},\"payload\":${payload}}]}" | cat
  echo
}

search_text() {
  local collection="$1"
  local query="$2"
  local limit="${3:-5}"

  local vector
  vector="$(embed_text "$query")"

  echo "[INFO] Searching ${collection} (limit=${limit})"
  curl -fsS -X POST "${QDRANT_URL}/collections/${collection}/points/search" \
    -H 'Content-Type: application/json' \
    -d "{\"vector\":${vector},\"limit\":${limit},\"with_payload\":true}" | cat
  echo
}

run_smoke_test() {
  local collection="$1"
  local point_id="smoke_$(date +%s)"
  local text="team ai platform supports git skill sync and rag search"
  local query="git skill sync rag"

  echo "[INFO] Running vector store smoke test on ${collection}"
  create_collection "$collection" "$DEFAULT_VECTOR_SIZE" "$DEFAULT_DISTANCE" || true
  upsert_text "$collection" "$point_id" "$text" '{"source":"smoke-test","team":"platform"}'
  search_text "$collection" "$query" 3
  collection_stats "$collection"
  echo "[INFO] Smoke test completed."
}

main() {
  require_cmd curl
  require_cmd python3

  local cmd="${1:-}"
  if [[ -z "${cmd}" ]]; then
    print_usage
    exit 1
  fi

  case "${cmd}" in
    create)
      [[ $# -ge 2 ]] || { print_usage; exit 1; }
      create_collection "$2" "${3:-}" "${4:-}"
      ;;
    list)
      list_collections
      ;;
    stats)
      [[ $# -ge 2 ]] || { print_usage; exit 1; }
      collection_stats "$2"
      ;;
    delete)
      [[ $# -ge 2 ]] || { print_usage; exit 1; }
      delete_collection "$2"
      ;;
    upsert-text)
      [[ $# -ge 4 ]] || { print_usage; exit 1; }
      upsert_text "$2" "$3" "$4" "${5:-{}}"
      ;;
    search)
      [[ $# -ge 3 ]] || { print_usage; exit 1; }
      search_text "$2" "$3" "${4:-5}"
      ;;
    test)
      [[ $# -ge 2 ]] || { print_usage; exit 1; }
      run_smoke_test "$2"
      ;;
    *)
      print_usage
      exit 1
      ;;
  esac
}

main "$@"
