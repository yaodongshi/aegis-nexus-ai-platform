from __future__ import annotations

from datetime import UTC, datetime
from typing import List

from fastapi import APIRouter, Header

from ...settings_schemas import LocaleRecord, TranslationsRecord, UserSettingsRecord, UserSettingsUpdateRequest
from .users import resolve_user_from_auth_header

router = APIRouter()

_USER_SETTINGS: dict[str, dict] = {}

_SUPPORTED_LOCALES: list[dict] = [
    {"code": "zh-CN", "name": "中文（简体）"},
    {"code": "zh-TW", "name": "中文（繁體）"},
    {"code": "en-US", "name": "English (US)"},
    {"code": "ja-JP", "name": "日本語"},
    {"code": "ko-KR", "name": "한국어"},
]

_TRANSLATIONS: dict[str, dict] = {
    "zh-CN": {
        "common.save": "保存",
        "common.cancel": "取消",
        "common.delete": "删除",
        "common.edit": "编辑",
        "common.create": "新建",
        "common.search": "搜索",
        "common.confirm": "确认",
        "nav.dashboard": "仪表盘",
        "nav.teams": "团队",
        "nav.projects": "项目",
        "nav.tasks": "任务",
        "nav.agents": "智能体",
        "nav.knowledge": "知识库",
        "nav.plugins": "插件",
        "nav.settings": "设置",
    },
    "en-US": {
        "common.save": "Save",
        "common.cancel": "Cancel",
        "common.delete": "Delete",
        "common.edit": "Edit",
        "common.create": "Create",
        "common.search": "Search",
        "common.confirm": "Confirm",
        "nav.dashboard": "Dashboard",
        "nav.teams": "Teams",
        "nav.projects": "Projects",
        "nav.tasks": "Tasks",
        "nav.agents": "Agents",
        "nav.knowledge": "Knowledge",
        "nav.plugins": "Plugins",
        "nav.settings": "Settings",
    },
}


def _default_settings(user_id: str) -> dict:
    return {
        "user_id": user_id,
        "language": "zh-CN",
        "theme": "light",
        "timezone": "Asia/Shanghai",
        "notifications_enabled": True,
        "updated_at": datetime.now(UTC),
    }


@router.get("/me", response_model=UserSettingsRecord)
def get_my_settings(authorization: str | None = Header(default=None)):
    current = resolve_user_from_auth_header(authorization)
    uid = current["id"]
    if uid not in _USER_SETTINGS:
        _USER_SETTINGS[uid] = _default_settings(uid)
    return UserSettingsRecord(**_USER_SETTINGS[uid])


@router.put("/me", response_model=UserSettingsRecord)
def update_my_settings(payload: UserSettingsUpdateRequest, authorization: str | None = Header(default=None)):
    current = resolve_user_from_auth_header(authorization)
    uid = current["id"]
    if uid not in _USER_SETTINGS:
        _USER_SETTINGS[uid] = _default_settings(uid)
    updates = payload.model_dump(exclude_none=True)
    _USER_SETTINGS[uid].update(updates)
    _USER_SETTINGS[uid]["updated_at"] = datetime.now(UTC)
    return UserSettingsRecord(**_USER_SETTINGS[uid])


@router.get("/locales", response_model=List[LocaleRecord])
def list_locales():
    return [LocaleRecord(**loc) for loc in _SUPPORTED_LOCALES]


@router.get("/translations/{locale_code}", response_model=TranslationsRecord)
def get_translations(locale_code: str):
    from fastapi import HTTPException, status
    translations = _TRANSLATIONS.get(locale_code)
    if translations is None:
        # Fall back to en-US for unsupported locales
        translations = _TRANSLATIONS.get("en-US", {})
    return TranslationsRecord(locale=locale_code, translations=translations)
