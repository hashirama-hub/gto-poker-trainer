"""Model checkpoint routes."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gto.db import get_session
from gto.db.models import ModelCheckpoint
from gto.api.schemas import ModelCheckpointCreate, ModelCheckpointResponse

router = APIRouter()


@router.post("", response_model=ModelCheckpointResponse, status_code=201)
async def create_model(
    data: ModelCheckpointCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    checkpoint = ModelCheckpoint(**data.model_dump())
    session.add(checkpoint)
    await session.commit()
    await session.refresh(checkpoint)
    return checkpoint


@router.get("", response_model=list[ModelCheckpointResponse])
async def list_models(
    session: Annotated[AsyncSession, Depends(get_session)],
    model_type: str | None = None,
    active_only: bool = True,
):
    query = select(ModelCheckpoint)
    if model_type:
        query = query.where(ModelCheckpoint.model_type == model_type)
    if active_only:
        query = query.where(ModelCheckpoint.is_active == True)
    query = query.order_by(ModelCheckpoint.created_at.desc())
    result = await session.execute(query)
    return result.scalars().all()


@router.get("/{model_id}", response_model=ModelCheckpointResponse)
async def get_model(
    model_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    result = await session.execute(select(ModelCheckpoint).where(ModelCheckpoint.id == model_id))
    checkpoint = result.scalar_one_or_none()
    if not checkpoint:
        raise HTTPException(404, "Model not found")
    return checkpoint


@router.patch("/{model_id}", response_model=ModelCheckpointResponse)
async def update_model(
    model_id: UUID,
    data: dict,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    result = await session.execute(select(ModelCheckpoint).where(ModelCheckpoint.id == model_id))
    checkpoint = result.scalar_one_or_none()
    if not checkpoint:
        raise HTTPException(404, "Model not found")
    for key, value in data.items():
        if hasattr(checkpoint, key):
            setattr(checkpoint, key, value)
    await session.commit()
    await session.refresh(checkpoint)
    return checkpoint


@router.delete("/{model_id}", status_code=204)
async def delete_model(
    model_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    result = await session.execute(select(ModelCheckpoint).where(ModelCheckpoint.id == model_id))
    checkpoint = result.scalar_one_or_none()
    if not checkpoint:
        raise HTTPException(404, "Model not found")
    await session.delete(checkpoint)
    await session.commit()