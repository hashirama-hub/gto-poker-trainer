"""API routes for quiz/training."""
import random
import time
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
    QuizAction,
    QuizHandResponse,
    QuizResultResponse,
    QuizStartRequest,
    QuizSubmitRequest,
    QuizSummaryResponse,
)
from gto.db import get_session
from gto.db.models import QuizHand, QuizSession, User
from gto.trainer.engine import (
    Question,
    make_flop_question,
    make_icm_pushfold_question,
    make_preflop_question,
    make_pushfold_question,
    random_hand_name,
    score_choice,
)
from gto.trainer.models import flop_subgame, full100_model, icm_pushfold, pushfold_model

router = APIRouter(tags=["quiz"])


def question_to_response(q: Question, hand_number: int, total: int, hand_id: UUID = None) -> QuizHandResponse:
    actions = [
        QuizAction(
            label=label,
            gto_pct=q.gto.get(label, 0.0) * 100,
            ev_bb=q.ev.get(label, 0.0),
        )
        for label in q.actions
    ]
    return QuizHandResponse(
        id=hand_id or UUID(int=0),
        hand_number=hand_number,
        hero_position=q.player,
        hand_name=q.hand,
        board_cards=None,
        actions=actions,
        prompt=f"Q{hand_number}/{total} \u2014 {q.prompt}",
    )


@router.post("/start", response_model=QuizHandResponse)
async def start_quiz(
    request: QuizStartRequest,
    session: AsyncSession = Depends(get_session),
):
    # Create or get anonymous user
    anon_id = UUID("00000000-0000-0000-0000-000000000000")
    result = await session.execute(select(User).where(User.id == anon_id))
    anon_user = result.scalar_one_or_none()
    if not anon_user:
        anon_user = User(
            id=anon_id,
            username="anonymous",
            email=None,
            hashed_password="",
        )
        session.add(anon_user)
        await session.flush()
    
    quiz_session = QuizSession(
        user_id=anon_id,
        mode=request.mode,
        hands_total=request.hands,
        hands_answered=0,
        config=request.config,
    )
    session.add(quiz_session)
    await session.flush()
    
    rng = random.Random()
    if request.mode == "pushfold":
        depth = request.config.get("bb", 0) or float(rng.randint(8, 25))
        player = 0 if request.config.get("position", "sb") == "sb" else 1
        q = make_pushfold_question(rng, depth, player)
    elif request.mode == "icm":
        iterations = request.config.get("iterations", 60000)
        player = 0 if request.config.get("position", "sb") == "sb" else 1
        q, _ = make_icm_pushfold_question(rng, iterations=iterations, player=player)
    elif request.mode == "preflop":
        player = 0 if request.config.get("position", "sb") == "sb" else 1
        solver = full100_model()
        q = make_preflop_question(rng, solver, player)
    elif request.mode == "flop":
        iterations = 6000 if request.config.get("fast") else 20000
        board = None
        if request.config.get("board"):
            board = tuple(int(x) for x in request.config["board"].split(","))
        q, _ = make_flop_question(rng, board, iterations)
    else:
        raise HTTPException(400, f"Unknown mode: {request.mode}")
    
    quiz_hand = QuizHand(
        session_id=quiz_session.id,
        hand_number=1,
        hero_position=q.player,
        hand_name=q.hand,
        board_cards=None,
        actions=[{"label": a, "gto_pct": q.gto.get(a, 0), "ev_bb": q.ev.get(a, 0)} for a in q.actions],
    )
    session.add(quiz_hand)
    await session.commit()
    await session.refresh(quiz_hand)
    
    return question_to_response(q, 1, request.hands, quiz_hand.id)


@router.post("/{session_id}/submit", response_model=QuizResultResponse)
async def submit_answer(
    session_id: UUID,
    request: QuizSubmitRequest,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(QuizHand).where(QuizHand.id == request.hand_id, QuizHand.session_id == session_id)
    )
    quiz_hand = result.scalar_one_or_none()
    if not quiz_hand:
        raise HTTPException(404, "Question not found")
    
    if quiz_hand.user_choice is not None:
        raise HTTPException(400, "Already answered")
    
    ev_dict = {a["label"]: a["ev_bb"] for a in quiz_hand.actions}
    gto_dict = {a["label"]: a["gto_pct"] for a in quiz_hand.actions}
    best = max(ev_dict, key=ev_dict.get)
    worst = min(ev_dict, key=ev_dict.get)
    
    score = score_choice(request.choice, ev_dict)
    verdict = "GTO" if request.choice == best else ("terrible" if request.choice == worst else "ok")
    
    quiz_hand.user_choice = request.choice
    quiz_hand.user_ev_bb = ev_dict.get(request.choice, 0)
    quiz_hand.gto_best_action = best
    quiz_hand.score = int(score)
    
    result = await session.execute(select(QuizSession).where(QuizSession.id == session_id))
    quiz_session = result.scalar_one()
    quiz_session.hands_answered += 1
    
    await session.commit()
    
    return QuizResultResponse(
        score=int(score),
        verdict=verdict,
        gto_best=best,
        gto_pct=gto_dict.get(best, 0) * 100,
        user_ev_bb=ev_dict.get(request.choice, 0),
        best_ev_bb=ev_dict[best],
        worst_ev_bb=ev_dict[worst],
    )


@router.get("/{session_id}/next", response_model=QuizHandResponse)
async def next_question(
    session_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(QuizSession).where(QuizSession.id == session_id))
    quiz_session = result.scalar_one_or_none()
    if not quiz_session:
        raise HTTPException(404, "Quiz session not found")
    
    if quiz_session.hands_answered >= quiz_session.hands_total:
        raise HTTPException(400, "Quiz completed")
    
    rng = random.Random()
    hand_num = quiz_session.hands_answered + 1
    
    if quiz_session.mode == "pushfold":
        depth = float(rng.randint(8, 25))
        q = make_pushfold_question(rng, depth, 0)
    elif quiz_session.mode == "icm":
        q, _ = make_icm_pushfold_question(rng)
    elif quiz_session.mode == "preflop":
        solver = full100_model()
        q = make_preflop_question(rng, solver, 0)
    elif quiz_session.mode == "flop":
        q, _ = make_flop_question(rng)
    else:
        raise HTTPException(400, f"Unknown mode: {quiz_session.mode}")
    
    quiz_hand = QuizHand(
        session_id=session_id,
        hand_number=hand_num,
        hero_position=q.player,
        hand_name=q.hand,
        board_cards=None,
        actions=[{"label": a, "gto_pct": q.gto.get(a, 0), "ev_bb": q.ev.get(a, 0)} for a in q.actions],
    )
    session.add(quiz_hand)
    await session.commit()
    await session.refresh(quiz_hand)
    
    return question_to_response(q, hand_num, quiz_session.hands_total, quiz_hand.id)


@router.get("/{session_id}/summary", response_model=QuizSummaryResponse)
async def get_summary(
    session_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(QuizSession).where(QuizSession.id == session_id))
    quiz_session = result.scalar_one_or_none()
    if not quiz_session:
        raise HTTPException(404, "Quiz session not found")
    
    return quiz_session