"""API routes for GTO strategy lookup."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gto.api.schemas import (
    GTOActionInfo,
    GTOHandInfo,
    GTOInfoRequest,
    GTOInfoResponse,
    ModelCheckpointCreate,
    ModelCheckpointResponse,
    TrainingRunCreate,
    TrainingRunResponse,
)
from gto.db import get_session
from gto.db.models import ModelCheckpoint, TrainingRun
from gto.trainer.models import full100_model, pushfold_model

router = APIRouter(tags=["gto"])


@router.post("/info", response_model=GTOInfoResponse)
async def get_gto_info(
    request: GTOInfoRequest,
    session: AsyncSession = Depends(get_session),
):
    hands_info = []
    
    if request.depth:
        # Push/fold model
        solver = pushfold_model(request.depth)
        eff = solver.cfg.stack // 100
        model_type = f"pushfold_{int(request.depth)}bb"
    else:
        # Full 100bb model
        solver = full100_model(request.model_path)
        eff = 100
        model_type = "full100"
    
    key = solver.root_key
    
    for hand in request.hands:
        strat = solver.strategy_for_hand(key, 0, hand.upper())
        samples = 400 if request.depth else 30
        ev = solver.ev_actions(key, 0, hand.upper(), samples=samples)
        
        actions = [
            GTOActionInfo(
                label=label,
                gto_pct=strat.get(label, 0.0) * 100,
                ev_bb=ev.get(label, 0.0),
            )
            for label in ev
        ]
        
        hands_info.append(GTOHandInfo(
            hand=hand.upper(),
            position="SB",
            effective_bb=eff,
            actions=actions,
        ))
    
    return GTOInfoResponse(model_type=model_type, hands=hands_info)


@router.post("/models", response_model=ModelCheckpointResponse, status_code=201)
async def create_model_checkpoint(
    data: ModelCheckpointCreate,
    session: AsyncSession = Depends(get_session),
):
    checkpoint = ModelCheckpoint(**data.model_dump())
    session.add(checkpoint)
    await session.commit()
    await session.refresh(checkpoint)
    return checkpoint


@router.get("/models", response_model=list[ModelCheckpointResponse])
async def list_models(
    model_type: str | None = None,
    active_only: bool = True,
    session: AsyncSession = Depends(get_session),
):
    query = select(ModelCheckpoint)
    if model_type:
        query = query.where(ModelCheckpoint.model_type == model_type)
    if active_only:
        query = query.where(ModelCheckpoint.is_active == True)
    query = query.order_by(ModelCheckpoint.created_at.desc())
    
    result = await session.execute(query)
    return result.scalars().all()


@router.get("/models/{model_id}", response_model=ModelCheckpointResponse)
async def get_model(
    model_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(ModelCheckpoint).where(ModelCheckpoint.id == model_id))
    checkpoint = result.scalar_one_or_none()
    if not checkpoint:
        raise HTTPException(404, "Model not found")
    return checkpoint


@router.post("/training", response_model=TrainingRunResponse, status_code=201)
async def start_training(
    data: TrainingRunCreate,
    session: AsyncSession = Depends(get_session),
):
    # Verify checkpoint exists
    result = await session.execute(select(ModelCheckpoint).where(ModelCheckpoint.id == data.checkpoint_id))
    checkpoint = result.scalar_one_or_none()
    if not checkpoint:
        raise HTTPException(404, "Checkpoint not found")
    
    run = TrainingRun(
        checkpoint_id=data.checkpoint_id,
        target_iterations=data.target_iterations,
        git_commit=data.git_commit,
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return run


@router.get("/training", response_model=list[TrainingRunResponse])
async def list_training_runs(
    checkpoint_id: UUID | None = None,
    session: AsyncSession = Depends(get_session),
):
    query = select(TrainingRun).order_by(TrainingRun.started_at.desc())
    if checkpoint_id:
        query = query.where(TrainingRun.checkpoint_id == checkpoint_id)
    
    result = await session.execute(query)
    return result.scalars().all()