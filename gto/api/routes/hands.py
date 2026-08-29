"""Hand history routes."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from gto.db import get_session
from gto.db.models import HandHistory
from gto.api.schemas import HandHistoryCreate, HandHistoryResponse

router = APIRouter()


@router.post("", response_model=HandHistoryResponse, status_code=201)
async def create_hand(
    hand: HandHistoryCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user_id: UUID = "00000000-0000-0000-0000-000000000000",  # TODO: get from auth
):
    db_hand = HandHistory(user_id=current_user_id, **hand.model_dump())
    session.add(db_hand)
    await session.commit()
    await session.refresh(db_hand)
    return db_hand


@router.get("", response_model=list[HandHistoryResponse])
async def list_hands(
    session: Annotated[AsyncSession, Depends(get_session)],
    page: int = 1,
    limit: int = 50,
    current_user_id: UUID = "00000000-0000-0000-0000-000000000000",
):
    offset = (page - 1) * limit
    result = await session.execute(
        select(HandHistory)
        .where(HandHistory.user_id == current_user_id)
        .order_by(HandHistory.played_at.desc().nullslast())
        .offset(offset)
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/stats")
async def hand_stats(
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user_id: UUID = "00000000-0000-0000-0000-000000000000",
):
    result = await session.execute(
        select(
            func.count(HandHistory.id),
            func.avg(HandHistory.ev_diff_bb),
            func.sum(HandHistory.result_bb),
        ).where(HandHistory.user_id == current_user_id)
    )
    count, avg_ev_diff, total_result = result.one()
    return {
        "total_hands": count or 0,
        "avg_ev_diff_bb": round(avg_ev_diff or 0, 2),
        "total_result_bb": round(total_result or 0, 2),
    }


@router.post("/import")
async def import_hands(
    file: UploadFile = File(...),
    session: Annotated[AsyncSession, Depends(get_session)] = None,
    current_user_id: UUID = "00000000-0000-0000-0000-000000000000",
):
    # TODO: Parse PokerTracker/Holdem Manager format
    return {"imported": 0, "message": "Not implemented yet"}