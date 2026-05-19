from datetime import datetime
from typing import Any

from pydantic import BaseModel


class UserSettingsRecord(BaseModel):
    user_id: str
    language: str = "zh-CN"
    theme: str = "light"
    timezone: str = "Asia/Shanghai"
    notifications_enabled: bool = True
    updated_at: datetime


class UserSettingsUpdateRequest(BaseModel):
    language: str | None = None
    theme: str | None = None
    timezone: str | None = None
    notifications_enabled: bool | None = None


class LocaleRecord(BaseModel):
    code: str
    name: str


class TranslationsRecord(BaseModel):
    locale: str
    translations: dict[str, Any]
