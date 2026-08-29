"""SQLAlchemy models."""
import enum
from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from gto.db import Base


class ModelType(str, enum.Enum):
    PUSHFOLD = "pushfold"
    FULL100 = "full100"
    ICM = "icm"
    FLOP_SUBGAME = "flop_subgame"


class TrainingStatus(str, enum.Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class TournamentStatus(str, enum.Enum):
    REGISTERING = "registering"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TableStatus(str, enum.Enum):
    WAITING = "waiting"
    PLAYING = "playing"
    HAND_IN_PROGRESS = "hand_in_progress"
    BALANCING = "balancing"
    CLOSED = "closed"


class Street(str, enum.Enum):
    PREFLOP = "preflop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"
    SHOWDOWN = "showdown"


class ActionType(str, enum.Enum):
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    BET = "bet"
    RAISE = "raise"
    ALL_IN = "all_in"
    POST_SB = "post_sb"
    POST_BB = "post_bb"
    POST_ANTE = "post_ante"


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(100), unique=True, index=True, nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    elo_rating: Mapped[int] = mapped_column(Integer, default=1000)
    is_active: Mapped[bool] = mapped_column(default=True)
    is_superuser: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    quiz_sessions: Mapped[list["QuizSession"]] = relationship(back_populates="user")
    hand_histories: Mapped[list["HandHistory"]] = relationship(back_populates="user")


class ModelCheckpoint(Base):
    __tablename__ = "model_checkpoints"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    model_type: Mapped[ModelType] = mapped_column(Enum(ModelType), nullable=False, index=True)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default={})
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    iterations: Mapped[int] = mapped_column(Integer, default=0)
    exploitability_bb: Mapped[float | None] = mapped_column(Float, nullable=True)
    exploitability_trials: Mapped[int | None] = mapped_column(Integer, nullable=True)
    parent_checkpoint_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("model_checkpoints.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    training_runs: Mapped[list["TrainingRun"]] = relationship(back_populates="checkpoint")
    exploitability_logs: Mapped[list["ExploitabilityLog"]] = relationship(back_populates="checkpoint")


class TrainingRun(Base):
    __tablename__ = "training_runs"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    checkpoint_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("model_checkpoints.id"), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    target_iterations: Mapped[int] = mapped_column(Integer, nullable=False)
    completed_iterations: Mapped[int] = mapped_column(Integer, default=0)
    iterations_per_second: Mapped[float | None] = mapped_column(Float, nullable=True)
    final_exploitability_bb: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[TrainingStatus] = mapped_column(Enum(TrainingStatus), default=TrainingStatus.RUNNING, index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    git_commit: Mapped[str | None] = mapped_column(String(40), nullable=True)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default={})

    checkpoint: Mapped["ModelCheckpoint"] = relationship(back_populates="training_runs")
    exploitability_logs: Mapped[list["ExploitabilityLog"]] = relationship(back_populates="training_run")


class ExploitabilityLog(Base):
    __tablename__ = "exploitability_logs"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    checkpoint_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("model_checkpoints.id"), nullable=False, index=True)
    training_run_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("training_runs.id"), nullable=True, index=True)
    iteration: Mapped[int] = mapped_column(Integer, nullable=False)
    exploitability_bb: Mapped[float] = mapped_column(Float, nullable=False)
    br0_bb: Mapped[float] = mapped_column(Float, nullable=False)
    br1_bb: Mapped[float] = mapped_column(Float, nullable=False)
    trials: Mapped[int] = mapped_column(Integer, nullable=False)
    boards_per_trial: Mapped[int] = mapped_column(Integer, nullable=False)
    measured_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    checkpoint: Mapped["ModelCheckpoint"] = relationship(back_populates="exploitability_logs")
    training_run: Mapped["TrainingRun | None"] = relationship(back_populates="exploitability_logs")

    __table_args__ = (Index("ix_exploitability_checkpoint_iteration", "checkpoint_id", "iteration"),)


class QuizSession(Base):
    __tablename__ = "quiz_sessions"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    mode: Mapped[str] = mapped_column(String(50), nullable=False)
    hands_total: Mapped[int] = mapped_column(Integer, nullable=False)
    hands_answered: Mapped[int] = mapped_column(Integer, default=0)
    avg_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default={})
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship(back_populates="quiz_sessions")
    hands: Mapped[list["QuizHand"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class QuizHand(Base):
    __tablename__ = "quiz_hands"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("quiz_sessions.id"), nullable=False, index=True)
    hand_number: Mapped[int] = mapped_column(Integer, nullable=False)
    hero_position: Mapped[int] = mapped_column(Integer, nullable=False)  # 0=SB, 1=BB
    hand_name: Mapped[str] = mapped_column(String(10), nullable=False)
    board_cards: Mapped[str | None] = mapped_column(String(50), nullable=True)
    actions: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=[])
    gto_best_action: Mapped[str | None] = mapped_column(String(20), nullable=True)
    user_choice: Mapped[str | None] = mapped_column(String(20), nullable=True)
    user_ev_bb: Mapped[float | None] = mapped_column(Float, nullable=True)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    session: Mapped["QuizSession"] = relationship(back_populates="hands")


class HandHistory(Base):
    __tablename__ = "hand_histories"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    tournament_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    hand_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hero_position: Mapped[str | None] = mapped_column(String(20), nullable=True)
    hero_hand: Mapped[str] = mapped_column(String(10), nullable=False)
    board: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    actions: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    pot_size_bb: Mapped[float | None] = mapped_column(Float, nullable=True)
    result_bb: Mapped[float | None] = mapped_column(Float, nullable=True)
    gto_ev_bb: Mapped[float | None] = mapped_column(Float, nullable=True)
    ev_diff_bb: Mapped[float | None] = mapped_column(Float, nullable=True)
    played_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="hand_histories")

    __table_args__ = (
        Index("ix_hand_history_user_played", "user_id", "played_at"),
        UniqueConstraint("tournament_id", "hand_number", name="uq_tournament_hand"),
    )