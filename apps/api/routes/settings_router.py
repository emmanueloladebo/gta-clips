"""
Settings API routes: dynamic configuration of AI Highlight engines (9router vs Groq),
models, and cost controls.
"""
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.shared.config import settings
from packages.shared.database import get_db
from packages.shared.models import SystemConfig, User, AuditEvent
from apps.api.auth import require_current_user

router = APIRouter(prefix="/api/settings", tags=["settings"])


class AiModelSettings(BaseModel):
    router_enabled: bool
    primary_provider: str  # "9router" | "groq"
    router_model_id: str
    groq_model_id: str
    router_available: bool
    groq_available: bool


class AiModelSettingsUpdate(BaseModel):
    router_enabled: Optional[bool] = None
    primary_provider: Optional[str] = None
    router_model_id: Optional[str] = None
    groq_model_id: Optional[str] = None


async def get_or_set_config(db: AsyncSession, key: str, default_val: str) -> str:
    stmt = select(SystemConfig).where(SystemConfig.key == key)
    res = (await db.execute(stmt)).scalar_one_or_none()
    if res:
        return res.value
    # Seed default
    new_cfg = SystemConfig(key=key, value=default_val)
    db.add(new_cfg)
    await db.flush()
    return default_val


async def set_config(db: AsyncSession, key: str, val: str) -> None:
    stmt = select(SystemConfig).where(SystemConfig.key == key)
    res = (await db.execute(stmt)).scalar_one_or_none()
    if res:
        res.value = val
    else:
        db.add(SystemConfig(key=key, value=val))


@router.get("/ai-models", response_model=AiModelSettings)
async def get_ai_model_settings(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_current_user)
):
    """Get active AI highlight extraction engine settings."""
    router_enabled_str = await get_or_set_config(db, "router_enabled", "true")
    primary_provider = await get_or_set_config(db, "primary_provider", "9router")
    router_model_id = await get_or_set_config(db, "router_model_id", settings.ROUTER_MODEL_ID or "openai/gpt-6-luna")
    groq_model_id = await get_or_set_config(db, "groq_model_id", settings.GROQ_MODEL_ID or "openai/gpt-oss-120b")
    await db.commit()

    return AiModelSettings(
        router_enabled=(router_enabled_str.lower() == "true"),
        primary_provider=primary_provider,
        router_model_id=router_model_id,
        groq_model_id=groq_model_id,
        router_available=bool(settings.ROUTER_API_KEY),
        groq_available=bool(settings.GROQ_API_KEY),
    )


@router.patch("/ai-models", response_model=AiModelSettings)
async def update_ai_model_settings(
    payload: AiModelSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_current_user)
):
    """Update active AI highlight extraction engine settings."""
    if payload.router_enabled is not None:
        await set_config(db, "router_enabled", "true" if payload.router_enabled else "false")
    if payload.primary_provider is not None:
        if payload.primary_provider not in ("9router", "groq"):
            raise HTTPException(status_code=400, detail="Invalid provider. Must be '9router' or 'groq'.")
        await set_config(db, "primary_provider", payload.primary_provider)
    if payload.router_model_id is not None:
        await set_config(db, "router_model_id", payload.router_model_id.strip())
    if payload.groq_model_id is not None:
        await set_config(db, "groq_model_id", payload.groq_model_id.strip())

    db.add(AuditEvent(
        actor=user.username,
        action="update_ai_model_settings",
        target_type="system_config",
        details_json=payload.model_dump(exclude_unset=True)
    ))
    await db.commit()

    return await get_ai_model_settings(db, user)


@router.post("/ai-models/toggle-router", response_model=AiModelSettings)
async def toggle_router_engine(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_current_user)
):
    """Quick toggle to turn 9router ON/OFF to preserve API credits."""
    router_enabled_str = await get_or_set_config(db, "router_enabled", "true")
    new_val = "false" if router_enabled_str.lower() == "true" else "true"
    await set_config(db, "router_enabled", new_val)

    db.add(AuditEvent(
        actor=user.username,
        action="toggle_9router",
        target_type="system_config",
        details_json={"router_enabled": new_val == "true"}
    ))
    await db.commit()

    return await get_ai_model_settings(db, user)
