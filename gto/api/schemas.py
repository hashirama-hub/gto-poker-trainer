"""Pydantic schemas for API requests/responses."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# --- User ---
class UserBase(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: Optional[str] = Field(default=None, max_length=100)


class UserCreate(UserBase):
    password: str = Field(min_length=8)


class UserUpdate(BaseModel):
    email: Optional[str] = Field(default=None, max_length=100)
    password: Optional[str] = Field(default=None, min_length=8)


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    elo_rating: int
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# --- Quiz ---
class QuizAction(BaseModel):
    label: str
    gto_pct: float
    ev_bb: float


class QuizConfig(BaseModel):
    pass


class QuizStartRequest(BaseModel):
    mode: str  # pushfold, icm, preflop, flop
    hands: int = Field(default=10, ge=1, le=100)
    config: dict = Field(default_factory=dict)


class QuizHandResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    hand_number: int
    hero_position: int
    hand_name: str
    board_cards: Optional[str]
    actions: list[QuizAction]
    prompt: str


class QuizSubmitRequest(BaseModel):
    hand_id: UUID
    choice: str


class QuizResultResponse(BaseModel):
    score: int
    verdict: str  # GTO, ok, terrible
    gto_best: str
    gto_pct: float
    user_ev_bb: float
    best_ev_bb: float
    worst_ev_bb: float


class QuizSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    mode: str
    hands_total: int
    hands_answered: int
    avg_score: Optional[float]
    duration_seconds: Optional[int]
    created_at: datetime


# --- Hand History ---
class HandHistoryCreate(BaseModel):
    tournament_id: Optional[str] = None
    hand_number: Optional[int] = None
    hero_position: Optional[str] = None
    hero_hand: str
    board: Optional[list[str]] = None
    actions: Optional[list[dict]] = None
    pot_size_bb: Optional[float] = None
    result_bb: Optional[float] = None
    gto_ev_bb: Optional[float] = None
    played_at: Optional[datetime] = None


class HandHistoryResponse(HandHistoryCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    ev_diff_bb: Optional[float]
    imported_at: datetime


# --- Model Checkpoint ---
class ModelCheckpointCreate(BaseModel):
    name: str
    model_type: str  # pushfold, full100, icm, flop_subgame
    config: dict
    file_path: str
    file_size_bytes: Optional[int] = None
    iterations: int
    exploitability_bb: Optional[float] = None
    exploitability_trials: Optional[int] = None
    parent_checkpoint_id: Optional[UUID] = None


class ModelCheckpointResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    model_type: str
    config: dict
    file_path: str
    file_size_bytes: Optional[int]
    iterations: int
    exploitability_bb: Optional[float]
    exploitability_trials: Optional[int]
    parent_checkpoint_id: Optional[UUID]
    is_active: bool
    created_at: datetime


# --- Training Run ---
class TrainingRunCreate(BaseModel):
    checkpoint_id: UUID
    target_iterations: int
    git_commit: Optional[str] = None


class TrainingRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    checkpoint_id: UUID
    started_at: datetime
    completed_at: Optional[datetime]
    target_iterations: int
    completed_iterations: int
    iterations_per_second: Optional[float]
    final_exploitability_bb: Optional[float]
    status: str
    error_message: Optional[str]
    git_commit: Optional[str]


# --- Exploitability Log ---
class ExploitabilityLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    checkpoint_id: UUID
    training_run_id: Optional[UUID]
    iteration: int
    exploitability_bb: float
    br0_bb: float
    br1_bb: float
    trials: int
    boards_per_trial: int
    measured_at: datetime


# --- GTO Info ---
class GTOActionInfo(BaseModel):
    label: str
    gto_pct: float
    ev_bb: float


class GTOHandInfo(BaseModel):
    hand: str
    position: str  # "SB" or "BB"
    effective_bb: int
    actions: list[GTOActionInfo]


class GTOInfoRequest(BaseModel):
    hands: list[str]
    depth: Optional[float] = None  # for pushfold
    model_path: Optional[str] = None  # for full100


class GTOInfoResponse(BaseModel):
    model_type: str
    hands: list[GTOHandInfo]


# --- Health ---
class HealthResponse(BaseModel):
    status: str
    database: str
    redis: str
    version: str