#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
import sys
import time
from typing import Any
from urllib import error, request


@dataclass
class WorkflowConfig:
    base_url: str
    admin_token: str
    applicant_id: str
    default_approval_reason: str
    poll_seconds: int
    once: bool


def _headers(admin_token: str) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if admin_token:
        headers["X-Admin-Token"] = admin_token
    return headers


def api_call(
    base_url: str,
    admin_token: str,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")

    req = request.Request(
        f"{base_url.rstrip('/')}{path}",
        method=method,
        data=body,
        headers=_headers(admin_token),
    )
    try:
        with request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
            data = json.loads(raw) if raw else {}
            return int(getattr(resp, "status", 200)), data
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8") if exc.fp else ""
        data: dict[str, Any] = {}
        if raw:
            try:
                data = json.loads(raw)
            except Exception:
                data = {"detail": raw}
        return int(exc.code), data


def _must_ok(status: int, body: dict[str, Any], action: str) -> dict[str, Any]:
    if status not in {200, 201}:
        raise RuntimeError(f"{action} failed: status={status}, body={body}")
    return body


def _get_all_skill_updates(base_url: str, admin_token: str) -> list[dict[str, Any]]:
    status, body = api_call(
        base_url,
        admin_token,
        "GET",
        "/api/skill-updates?limit=200&offset=0",
    )
    payload = _must_ok(status, body, "list skill updates")
    return list(payload.get("items") or [])


def _get_all_approvals(base_url: str, admin_token: str) -> list[dict[str, Any]]:
    status, body = api_call(
        base_url,
        admin_token,
        "GET",
        "/api/approvals?limit=200&offset=0",
    )
    payload = _must_ok(status, body, "list approvals")
    return list(payload.get("items") or [])


def _approval_key(record: dict[str, Any]) -> tuple[str, str]:
    return (str(record.get("action") or ""), str(record.get("resource_id") or ""))


def run_once(cfg: WorkflowConfig) -> None:
    updates = _get_all_skill_updates(cfg.base_url, cfg.admin_token)
    approvals = _get_all_approvals(cfg.base_url, cfg.admin_token)

    draft_updates = [u for u in updates if (u.get("status") == "draft")]
    approvals_by_key: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for ap in approvals:
        approvals_by_key.setdefault(_approval_key(ap), []).append(ap)

    submitted = 0
    applied = 0

    # Stage 1: automatically submit approval tickets for each draft update.
    for update in draft_updates:
        update_id = str(update.get("id") or "")
        if not update_id:
            continue
        key = ("apply_skill_update", update_id)
        related = approvals_by_key.get(key, [])
        has_open_or_done = any(
            (item.get("status") in {"pending", "approved"}) for item in related
        )
        if has_open_or_done:
            continue

        payload = {
            "applicant_id": cfg.applicant_id,
            "action": "apply_skill_update",
            "resource_id": update_id,
            "reason": cfg.default_approval_reason,
        }
        status, body = api_call(
            cfg.base_url,
            cfg.admin_token,
            "POST",
            "/api/approvals/submit",
            payload,
        )
        _must_ok(status, body, f"submit approval for {update_id}")
        submitted += 1

    # Refresh approvals after submission.
    approvals = _get_all_approvals(cfg.base_url, cfg.admin_token)
    approved_ids = {
        str(item.get("resource_id") or "")
        for item in approvals
        if item.get("action") == "apply_skill_update"
        and item.get("status") == "approved"
    }

    # Stage 2: apply only updates that are already approved by human.
    for update in draft_updates:
        update_id = str(update.get("id") or "")
        if not update_id or update_id not in approved_ids:
            continue
        status, body = api_call(
            cfg.base_url,
            cfg.admin_token,
            "POST",
            f"/api/skill-updates/{update_id}/apply",
            {},
        )
        _must_ok(status, body, f"apply approved update {update_id}")
        applied += 1

    print(
        json.dumps(
            {
                "draft_updates": len(draft_updates),
                "approval_submitted": submitted,
                "approved_and_applied": applied,
            },
            ensure_ascii=False,
        )
    )


def parse_args() -> WorkflowConfig:
    parser = argparse.ArgumentParser(
        description=(
            "Auto-evolution workflow: auto-submit approvals for draft skill updates, "
            "then auto-apply only human-approved updates."
        )
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("TEAM_AI_PLATFORM_BASE_URL", "http://localhost:3000"),
        help="Platform base URL, default from TEAM_AI_PLATFORM_BASE_URL or http://localhost:3000",
    )
    parser.add_argument(
        "--admin-token",
        default=os.getenv("TEAM_AI_PLATFORM_ADMIN_TOKEN", ""),
        help="Admin token, default from TEAM_AI_PLATFORM_ADMIN_TOKEN",
    )
    parser.add_argument(
        "--applicant-id",
        default=os.getenv("EVOLUTION_APPLICANT_ID", "evolution-bot"),
        help="Applicant id used when creating approval requests",
    )
    parser.add_argument(
        "--reason",
        default=os.getenv(
            "EVOLUTION_APPROVAL_REASON",
            "Auto-generated by evolution workflow; pending final human approval.",
        ),
        help="Reason field when submitting approval requests",
    )
    parser.add_argument(
        "--poll-seconds",
        type=int,
        default=int(os.getenv("EVOLUTION_POLL_SECONDS", "30")),
        help="Loop interval in seconds for daemon mode",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit (default is loop mode)",
    )
    args = parser.parse_args()

    return WorkflowConfig(
        base_url=args.base_url,
        admin_token=args.admin_token,
        applicant_id=args.applicant_id,
        default_approval_reason=args.reason,
        poll_seconds=max(5, args.poll_seconds),
        once=bool(args.once),
    )


def main() -> int:
    cfg = parse_args()
    try:
        if cfg.once:
            run_once(cfg)
            return 0

        while True:
            run_once(cfg)
            time.sleep(cfg.poll_seconds)
    except KeyboardInterrupt:
        print("stopped")
        return 0
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
