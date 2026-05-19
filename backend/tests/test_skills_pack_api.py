from fastapi.testclient import TestClient

import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).parents[2])) if str(pathlib.Path(__file__).parents[2]) not in sys.path else None
from backend.app.main import app


def test_skill_pack_export_and_zip():
    with TestClient(app) as client:
        create_resp = client.post(
            "/api/skills",
            json={
                "name": "Pack Test Skill",
                "description": "desc",
                "system_prompt": "be helpful",
                "category": "general",
                "tags": ["pack"],
            },
        )
        assert create_resp.status_code == 201
        skill_id = create_resp.json()["id"]

        pack_resp = client.get(f"/api/skills/{skill_id}/pack/claude-code")
        assert pack_resp.status_code == 200
        payload = pack_resp.json()
        assert payload["protocol_version"] == "1.0"
        assert payload["target"] == "claude-code"
        assert len(payload["files"]) >= 2
        assert any(item["path"].endswith("SYSTEM_PROMPT.md") for item in payload["files"])

        zip_resp = client.get(f"/api/skills/{skill_id}/pack-zip/claude-code.zip")
        assert zip_resp.status_code == 200
        assert zip_resp.headers["content-type"].startswith("application/zip")
        assert len(zip_resp.content) > 20


def test_skill_pack_invalid_target_returns_400():
    with TestClient(app) as client:
        create_resp = client.post(
            "/api/skills",
            json={
                "name": "Pack Invalid Target",
                "description": "desc",
                "system_prompt": "be precise",
                "category": "general",
                "tags": [],
            },
        )
        assert create_resp.status_code == 201
        skill_id = create_resp.json()["id"]

        resp = client.get(f"/api/skills/{skill_id}/pack/unknown-client")
        assert resp.status_code == 400
