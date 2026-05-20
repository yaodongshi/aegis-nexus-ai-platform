from __future__ import annotations

from pathlib import Path


def detect_stack_tags(workspace: Path) -> set[str]:
    tags: set[str] = set()

    has_pyproject = (workspace / "pyproject.toml").exists()
    has_requirements = (workspace / "requirements.txt").exists()
    if has_pyproject or has_requirements:
        tags.update({"python"})
    if (workspace / "package.json").exists():
        tags.update({"javascript", "typescript", "node"})
    if (workspace / "go.mod").exists():
        tags.update({"go"})
    if (workspace / "Cargo.toml").exists():
        tags.update({"rust"})
    if _has_odoo_manifest(workspace):
        tags.update({"odoo", "python", "erp"})

    return tags


def skill_matches_stack(skill_tags: list[str], stack_tags: set[str]) -> bool:
    if not stack_tags:
        return True
    normalized = {
        str(tag).strip().lower()
        for tag in skill_tags
        if str(tag).strip()
    }
    if not normalized:
        return True
    if "general" in normalized:
        return True
    return bool(normalized & stack_tags)


def _has_odoo_manifest(workspace: Path) -> bool:
    if (workspace / "__manifest__.py").exists():
        return True
    addons = workspace / "addons"
    if not addons.exists() or not addons.is_dir():
        return False
    for manifest in addons.glob("*/__manifest__.py"):
        if manifest.is_file():
            return True
    return False
