#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
WORKSPACE_ROOT="$(cd "${PROJECT_ROOT}/.." && pwd)"

VENV_PYTHON="${WORKSPACE_ROOT}/.venv/bin/python"
DEFAULT_TEST_TARGETS=(
	"backend/tests/test_learning_loop.py"
	"backend/tests/test_skills_pack_api.py"
	"backend/tests/test_users_auth.py"
)

RUN_TESTS=1
RUN_FRONTEND_BUILD=1
COMPOSE_BUILD=1
COMPOSE_UP=1

print_help() {
	cat <<'EOF'
Usage: bash scripts/dev_build_and_up.sh [options]

默认流程（建议每次开发完成后执行一次）：
1) 使用项目根目录 .venv 跑后端测试
2) 在 frontend 目录执行 npm run build
3) 执行 docker compose up -d --build

Options:
	--skip-tests            跳过后端测试
	--skip-frontend-build   跳过前端本地构建
	--skip-compose-build    docker compose up 时不带 --build
	--no-up                 不执行 docker compose up
	-h, --help              查看帮助

Environment:
	TEST_TARGETS="..."      自定义 pytest 目标（空格分隔）
EOF
}

while [[ $# -gt 0 ]]; do
	case "$1" in
		--skip-tests)
			RUN_TESTS=0
			;;
		--skip-frontend-build)
			RUN_FRONTEND_BUILD=0
			;;
		--skip-compose-build)
			COMPOSE_BUILD=0
			;;
		--no-up)
			COMPOSE_UP=0
			;;
		-h|--help)
			print_help
			exit 0
			;;
		*)
			echo "[ERROR] Unknown option: $1" >&2
			print_help
			exit 2
			;;
	esac
	shift
done

if [[ ! -x "${VENV_PYTHON}" ]]; then
	echo "[ERROR] Missing Python in .venv: ${VENV_PYTHON}" >&2
	echo "[INFO] Please create/activate workspace .venv first." >&2
	exit 1
fi

if [[ ! -f "${PROJECT_ROOT}/docker-compose.yml" ]]; then
	echo "[ERROR] Missing docker-compose.yml: ${PROJECT_ROOT}/docker-compose.yml" >&2
	exit 1
fi

if [[ ! -f "${PROJECT_ROOT}/.env" ]]; then
	echo "[ERROR] Missing .env file in ${PROJECT_ROOT}" >&2
	echo "[INFO] Run: cp .env.example .env" >&2
	exit 1
fi

cd "${PROJECT_ROOT}"

if [[ ${RUN_TESTS} -eq 1 ]]; then
	if [[ -n "${TEST_TARGETS:-}" ]]; then
		read -r -a TEST_ARGS <<< "${TEST_TARGETS}"
	else
		TEST_ARGS=("${DEFAULT_TEST_TARGETS[@]}")
	fi

	echo "[STEP] Running backend tests with .venv python..."
	PYTHONPATH=backend "${VENV_PYTHON}" -m pytest -q "${TEST_ARGS[@]}"
fi

if [[ ${RUN_FRONTEND_BUILD} -eq 1 ]]; then
	echo "[STEP] Building frontend in team_ai_platform/frontend..."
	(
		cd "${PROJECT_ROOT}/frontend"
		npm run build
	)
fi

if [[ ${COMPOSE_UP} -eq 1 ]]; then
	if [[ ${COMPOSE_BUILD} -eq 1 ]]; then
		echo "[STEP] Starting docker stack with rebuild..."
		docker compose up -d --build
	else
		echo "[STEP] Starting docker stack without rebuild..."
		docker compose up -d
	fi

	FRONTEND_PORT="${FRONTEND_PORT:-3000}"
	OPEN_WEBUI_PORT="${OPEN_WEBUI_PORT:-9000}"
	echo "[OK] Stack is up."
	echo "[INFO] Frontend: http://localhost:${FRONTEND_PORT}"
	echo "[INFO] Backend docs: http://localhost:8000/docs"
	echo "[INFO] Open WebUI: http://localhost:${OPEN_WEBUI_PORT}"
fi
