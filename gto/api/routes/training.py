"""Training run routes."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gto.db import get_session
from gto.db.models import TrainingRun, ModelCheckpoint
from gto.api.schemas import TrainingRunCreate, TrainingRunResponse

router = APIRouter()


@router.post("", response_model=TrainingRunResponse, status_code=201)
async def start_training(
    data: TrainingRunCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    result = await session.execute(select(ModelCheckpoint).where(ModelCheckpoint.id == data.checkpoint_id))
    checkpoint = result.scalar_one_or_none()
    if not checkpoint:
        raise HTTPException(404, "Checkpoint not found")

    run = TrainingRun(
        checkpoint_id=data.checkpoint_id,
        target_iterations=data.target_iterations,
        git_commit=data.git_commit,
        status="running",
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)

    # TODO: Trigger Celery task to run training
    return run


@router.get("", response_model=list[TrainingRunResponse])
async def list_training_runs(
    session: Annotated[AsyncSession, Depends(get_session)],
    checkpoint_id: UUID | None = None,
):
    query = select(TrainingRun).order_by(TrainingRun.started_at.desc())
    if checkpoint_id:
        query = query.where(TrainingRun.checkpoint_id == checkpoint_id)
    result = await session.execute(query)
    return result.scalars().all()


@router.get("/{run_id}", response_model=TrainingRunResponse)
async def get_training_run(
    run_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    result = await session.execute(select(TrainingRun).where(TrainingRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Training run not found")
    return run


@router.post("/{run_id}/pause", response_model=TrainingRunResponse)
async def pause_training(
    run_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    result = await session.execute(select(TrainingRun).where(TrainingRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Training run not found")
    run.status = "paused"
    await session.commit()
    await session.refresh(run)
    return run


@router.post("/{run_id}/resume", response_model=TrainingRunResponse)
async def resume_training(
    run_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    result = await session.execute(select(TrainingRun).where(TrainingRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Training run not found")
    run.status = "running"
    await session.commit()
    await session.refresh(run)
    return run


@router.delete("/{run_id}", status_code=204)
async def cancel_training(
    run_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    result = await session.execute(select(TrainingRun).where(TrainingRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Training run not found")
    run.status = "failed"
    run.error_message = "Cancelled by user"
    await session.commit()