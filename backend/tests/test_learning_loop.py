from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.main import app


def test_report_creates_task_run_and_draft_update(monkeypatch) -> None:
    monkeypatch.delenv("TEAM_AI_PLATFORM_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("TEAM_AI_PLATFORM_AGENT_TOKEN", raising=False)
    monkeypatch.delenv("TEAM_AI_PLATFORM_DB_DSN", raising=False)

    with TestClient(app) as client:
        resp = client.post(
            "/api/task-runs/report",
            json={
                "tool_type": "codex",
                "user_id": "u_test",
                "task_title": "Fix flaky test",
                "summary": "Added deterministic fixture and stabilized retries.",
                "lessons_learned": "Always isolate network calls with fakes.",
                "proposed_skill_name": "Flaky Test Stabilizer",
                "proposed_system_prompt": "You are an expert at stabilizing flaky tests.",
                "proposed_user_prompt_template": "Analyze flaky failures and propose minimal fixes.",
            },
        )
        assert resp.status_code == 201, resp.text
        payload = resp.json()
        assert payload["task_run"]["id"].startswith("taskrun_")
        assert payload["skill_update"]["id"].startswith("skillupdate_")
        assert payload["skill_update"]["status"] == "draft"

        list_updates = client.get("/api/skill-updates")
        assert list_updates.status_code == 200, list_updates.text
        assert list_updates.json()["total"] >= 1


def test_apply_then_sync_local_exports_bundle(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("TEAM_AI_PLATFORM_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("TEAM_AI_PLATFORM_AGENT_TOKEN", raising=False)
    monkeypatch.delenv("TEAM_AI_PLATFORM_DB_DSN", raising=False)

    with TestClient(app) as client:
        report = client.post(
            "/api/task-runs/report",
            json={
                "tool_type": "codex",
                "user_id": "u_apply",
                "task_title": "Improve prompt quality",
                "summary": "Consolidated prompt constraints.",
                "proposed_skill_name": "Prompt Consolidator",
                "proposed_system_prompt": "You enforce strict prompt constraints.",
            },
        )
        assert report.status_code == 201, report.text
        update_id = report.json()["skill_update"]["id"]

        apply_resp = client.post(f"/api/skill-updates/{update_id}/apply", json={})
        assert apply_resp.status_code == 200, apply_resp.text
        applied = apply_resp.json()
        assert applied["status"] == "applied"
        assert applied["skill_id"]

        sync_resp = client.post(
            f"/api/skill-updates/{update_id}/sync",
            json={"mode": "local", "path": str(tmp_path)},
        )
        assert sync_resp.status_code == 200, sync_resp.text
        synced = sync_resp.json()
        assert synced["status"] == "synced"
        assert synced["export_path"]
        assert Path(synced["export_path"]).exists()


def test_sync_git_mode_supports_no_auto_commit(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("TEAM_AI_PLATFORM_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("TEAM_AI_PLATFORM_AGENT_TOKEN", raising=False)
    monkeypatch.delenv("TEAM_AI_PLATFORM_DB_DSN", raising=False)

    git_repo = tmp_path / "skill-repo"
    git_repo.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "-C", str(git_repo), "init"], check=True)

    with TestClient(app) as client:
        create_repo = client.post(
            "/api/git-repos",
            json={
                "name": "team-ai-skills",
                "path": str(git_repo),
                "branch": "feature-sync",
                "auto_commit": False,
                "make_active": True,
            },
        )
        assert create_repo.status_code == 201, create_repo.text
        repo_id = create_repo.json()["id"]

        list_repos = client.get("/api/git-repos")
        assert list_repos.status_code == 200, list_repos.text
        assert any(item["id"] == repo_id for item in list_repos.json()["items"])

        report = client.post(
            "/api/task-runs/report",
            json={
                "tool_type": "codex",
                "user_id": "u_git",
                "task_title": "Document API retries",
                "summary": "Added backoff best practices.",
                "proposed_skill_name": "API Retry Guide",
                "proposed_system_prompt": "You optimize API retry strategies.",
            },
        )
        assert report.status_code == 201, report.text
        update_id = report.json()["skill_update"]["id"]

        apply_resp = client.post(f"/api/skill-updates/{update_id}/apply", json={})
        assert apply_resp.status_code == 200, apply_resp.text

        sync_resp = client.post(
            f"/api/skill-updates/{update_id}/sync",
            json={"mode": "git", "repo_id": repo_id},
        )
        assert sync_resp.status_code == 200, sync_resp.text
        payload = sync_resp.json()
        assert payload["status"] == "synced"
        assert payload["git_repo_id"] == repo_id
        assert payload["git_commit_hash"] is None
        current_branch = subprocess.check_output(
            ["git", "-C", str(git_repo), "branch", "--show-current"],
            text=True,
        ).strip()
        assert current_branch == "feature-sync"


def test_git_repo_activate_switch(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("TEAM_AI_PLATFORM_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("TEAM_AI_PLATFORM_AGENT_TOKEN", raising=False)
    monkeypatch.delenv("TEAM_AI_PLATFORM_DB_DSN", raising=False)

    repo_a = tmp_path / "repo-a"
    repo_b = tmp_path / "repo-b"
    repo_a.mkdir(parents=True, exist_ok=True)
    repo_b.mkdir(parents=True, exist_ok=True)

    with TestClient(app) as client:
        first = client.post(
            "/api/git-repos",
            json={"name": "repo-a", "path": str(repo_a), "make_active": True},
        )
        assert first.status_code == 201, first.text

        second = client.post(
            "/api/git-repos",
            json={"name": "repo-b", "path": str(repo_b), "make_active": False},
        )
        assert second.status_code == 201, second.text
        second_id = second.json()["id"]

        activate = client.post(f"/api/git-repos/{second_id}/activate")
        assert activate.status_code == 200, activate.text
        assert activate.json()["is_active"] is True

        active = client.get("/api/git-repos/active")
        assert active.status_code == 200, active.text
        assert active.json()["id"] == second_id


def test_git_repo_probe(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("TEAM_AI_PLATFORM_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("TEAM_AI_PLATFORM_AGENT_TOKEN", raising=False)
    monkeypatch.delenv("TEAM_AI_PLATFORM_DB_DSN", raising=False)

    git_repo = tmp_path / "probe-repo"
    git_repo.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "-C", str(git_repo), "init"], check=True)

    with TestClient(app) as client:
        created = client.post(
            "/api/git-repos",
            json={"name": "probe-repo", "path": str(git_repo), "branch": "main", "make_active": True},
        )
        assert created.status_code == 201, created.text
        repo_id = created.json()["id"]

        probe = client.get(f"/api/git-repos/{repo_id}/probe")
        assert probe.status_code == 200, probe.text
        payload = probe.json()
        assert payload["repo_id"] == repo_id
        assert payload["path_exists"] is True
        assert payload["is_git_repo"] is True
        assert isinstance(payload["git_available"], bool)


def test_skill_hook_report_signature_and_idempotency(monkeypatch) -> None:
    monkeypatch.delenv("TEAM_AI_PLATFORM_ADMIN_TOKEN", raising=False)
    monkeypatch.setenv("TEAM_AI_PLATFORM_HOOK_SECRET", "hook-secret-test")
    monkeypatch.delenv("TEAM_AI_PLATFORM_DB_DSN", raising=False)

    payload = {
        "repository": "team-ai-skills",
        "branch": "main",
        "commit_sha": "abc123",
        "changed_files": [".claude/skills/repo-skill/SYSTEM_PROMPT.md"],
    }
    raw = json.dumps(payload).encode("utf-8")
    signature = "sha256=" + hmac.new(b"hook-secret-test", raw, hashlib.sha256).hexdigest()

    with TestClient(app) as client:
        first = client.post(
            "/api/skill-sync/hooks/report",
            content=raw,
            headers={
                "Content-Type": "application/json",
                "X-Hook-Signature": signature,
            },
        )
        assert first.status_code == 201, first.text
        first_payload = first.json()
        assert first_payload["created"] is True

        second = client.post(
            "/api/skill-sync/hooks/report",
            content=raw,
            headers={
                "Content-Type": "application/json",
                "X-Hook-Signature": signature,
            },
        )
        assert second.status_code == 201, second.text
        second_payload = second.json()
        assert second_payload["created"] is False
        assert second_payload["idempotency_key"] == first_payload["idempotency_key"]


def test_git_repo_pull_imports_and_conflicts(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("TEAM_AI_PLATFORM_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("TEAM_AI_PLATFORM_AGENT_TOKEN", raising=False)
    monkeypatch.delenv("TEAM_AI_PLATFORM_DB_DSN", raising=False)

    repo_dir = tmp_path / "pull-repo"
    repo_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "-C", str(repo_dir), "init"], check=True)
    branch = subprocess.check_output(
        ["git", "-C", str(repo_dir), "branch", "--show-current"],
        text=True,
    ).strip() or "main"

    first_bundle = {
        "schema_version": "1.0",
        "skill": {
            "name": "Repo Pull Skill",
            "description": "from repo",
            "system_prompt": "use repository knowledge",
            "category": "general",
            "tags": ["repo"],
        },
    }
    (repo_dir / "repo_pull.skill.json").write_text(json.dumps(first_bundle), encoding="utf-8")

    with TestClient(app) as client:
        created = client.post(
            "/api/git-repos",
            json={
                "name": "pull-repo",
                "path": str(repo_dir),
                "branch": branch,
                "make_active": True,
            },
        )
        assert created.status_code == 201, created.text
        repo_id = created.json()["id"]

        first_pull = client.post(f"/api/git-repos/{repo_id}/pull", json={})
        assert first_pull.status_code == 200, first_pull.text
        first_payload = first_pull.json()
        assert first_payload["imported_skills"] >= 1
        assert first_payload["conflicts"] == 0

        second_bundle = {
            "schema_version": "1.0",
            "skill": {
                "name": "Repo Pull Skill",
                "description": "from repo changed",
                "system_prompt": "updated prompt content",
                "category": "general",
                "tags": ["repo", "changed"],
            },
        }
        (repo_dir / "repo_pull.skill.json").write_text(json.dumps(second_bundle), encoding="utf-8")

        second_pull = client.post(f"/api/git-repos/{repo_id}/pull", json={})
        assert second_pull.status_code == 200, second_pull.text
        second_payload = second_pull.json()
        assert second_payload["conflicts"] >= 1
        assert len(second_payload["conflict_update_ids"]) >= 1


def test_hook_secret_rotate_status_and_event_list(monkeypatch) -> None:
    monkeypatch.delenv("TEAM_AI_PLATFORM_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("TEAM_AI_PLATFORM_HOOK_SECRET", raising=False)
    monkeypatch.delenv("TEAM_AI_PLATFORM_DB_DSN", raising=False)

    with TestClient(app) as client:
        rotate = client.post("/api/skill-sync/hooks/secret/rotate", json={})
        assert rotate.status_code == 200, rotate.text
        secret = rotate.json()["new_secret"]
        assert len(secret) >= 20

        status_resp = client.get("/api/skill-sync/hooks/secret")
        assert status_resp.status_code == 200, status_resp.text
        status_payload = status_resp.json()
        assert status_payload["source"] == "db"
        assert status_payload["masked_secret"]

        payload = {
            "event_id": f"evt-{uuid4().hex}",
            "repository": "rotated-secret-repo",
            "branch": "main",
            "commit_sha": uuid4().hex[:12],
            "changed_files": [".opencode/skills/demo/prompt.md"],
        }
        raw = json.dumps(payload).encode("utf-8")
        signature = "sha256=" + hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()

        report = client.post(
            "/api/skill-sync/hooks/report",
            content=raw,
            headers={
                "Content-Type": "application/json",
                "X-Hook-Signature": signature,
            },
        )
        assert report.status_code == 201, report.text
        hook_event_id = report.json()["hook_event_id"]

        found = False
        limit = 200
        offset = 0
        for _ in range(10):
            events = client.get("/api/skill-sync/hooks/events", params={"limit": limit, "offset": offset})
            assert events.status_code == 200, events.text
            items = events.json()["items"]
            matched = next((item for item in items if item.get("hook_event_id") == hook_event_id), None)
            if matched is not None:
                # DB 模式会保留上报仓库名；内存模式回落为 local。
                assert matched.get("repository") in {"rotated-secret-repo", "local"}
                found = True
                break
            if len(items) < limit:
                break
            offset += limit

        assert found


def test_passive_rag_ingest_accepts_and_rejects_items(monkeypatch) -> None:
    monkeypatch.delenv("TEAM_AI_PLATFORM_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("TEAM_AI_PLATFORM_AGENT_TOKEN", raising=False)
    monkeypatch.delenv("TEAM_AI_PLATFORM_DB_DSN", raising=False)

    payload = {
        "min_quality_score": 0.6,
        "items": [
            {
                "source_type": "commit",
                "source_id": f"c-{uuid4().hex[:10]}",
                "repository": "team-ai-skills",
                "title": "Fix retry strategy",
                "content": "Use exponential backoff and jitter for transient failures.",
                "quality_score": 0.82,
                "tags": ["reliability"],
                "metadata": {"commit_sha": "abc123"},
            },
            {
                "source_type": "issue",
                "source_id": f"i-{uuid4().hex[:10]}",
                "content": "This signal is too weak for ingestion",
                "quality_score": 0.2,
            },
            {
                "source_type": "task",
                "source_id": f"t-{uuid4().hex[:10]}",
                "content": "   ",
                "quality_score": 0.9,
            },
        ],
    }

    with TestClient(app) as client:
        resp = client.post("/api/skill-sync/rag/ingest", json=payload)
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["received"] == 3
        assert data["accepted"] == 1
        assert data["rejected"] == 2
        assert len(data["created_knowledge_ids"]) == 1

        reasons = {item["reason"] for item in data["rejected_items"]}
        assert "quality_below_threshold" in reasons
        assert "empty_content" in reasons


def test_passive_rag_ingest_respects_agent_token(monkeypatch) -> None:
    monkeypatch.delenv("TEAM_AI_PLATFORM_ADMIN_TOKEN", raising=False)
    monkeypatch.setenv("TEAM_AI_PLATFORM_AGENT_TOKEN", "agent-token-for-rag")
    monkeypatch.delenv("TEAM_AI_PLATFORM_DB_DSN", raising=False)

    payload = {
        "items": [
            {
                "source_type": "session",
                "source_id": f"s-{uuid4().hex[:10]}",
                "content": "Capture proven troubleshooting workflow for flaky network tests.",
                "quality_score": 0.9,
            }
        ]
    }

    with TestClient(app) as client:
        unauthorized = client.post("/api/skill-sync/rag/ingest", json=payload)
        assert unauthorized.status_code == 401, unauthorized.text

        authorized = client.post(
            "/api/skill-sync/rag/ingest",
            json=payload,
            headers={"X-Agent-Token": "agent-token-for-rag"},
        )
        assert authorized.status_code == 201, authorized.text
