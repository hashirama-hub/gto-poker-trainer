"""SQLAlchemy ORM models for GTO Poker Trainer."""
import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class QuizMode(str, enum.Enum):
    PUSHFOLD = "pushfold"
    ICM = "icm"
    PREFLOP = "preflop"
    FLOP = "flop"


class TrainingStatus(str, enum.Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    STOPPED = "stopped"
    FAILED = "failed"


class ModelType(str, enum.Enum):
    PUSHFOLD = "pushfold"
    FULL100 = "full100"
    ICM = "icm"
    FLOP_SUBGAME = "flop_subgame"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    elo_rating: Mapped[int] = mapped_column(Integer, default=1000)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    quiz_sessions: Mapped[list["QuizSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    hand_history: Mapped[list["HandHistory"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    model_bookmarks: Mapped[list["UserModelBookmark"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class QuizSession(Base):
    __tablename__ = "quiz_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    mode: Mapped[QuizMode] = mapped_column(nullable=False)
    hands_total: Mapped[int] = mapped_column(Integer, nullable=False)
    hands_answered: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="quiz_sessions")
    hands: Mapped[list["QuizHand"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="QuizHand.hand_number"
    )

    __table_args__ = (
        Index("ix_quiz_sessions_user_created", "user_id", "created_at"),
    )


class QuizHand(Base):
    __tablename__ = "quiz_hands"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("quiz_sessions.id", ondelete="CASCADE"), nullable=False
    )
    hand_number: Mapped[int] = mapped_column(Integer, nullable=False)
    hero_position: Mapped[int] = mapped_column(Integer, nullable=False)  # 0=SB, 1=BB
    hand_name: Mapped[str] = mapped_column(String(10), nullable=False)
    board_cards: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    actions: Mapped[dict] = mapped_column(JSON, nullable=False)
    user_choice: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    user_ev_bb: Mapped[Optional[float]] = mapped_column(Numeric(8, 3), nullable=True)
    gto_best_action: Mapped[str] = mapped_column(String(20), nullable=False)
    score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    time_taken_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    session: Mapped["QuizSession"] = relationship(back_populates="hands")

    __table_args__ = (
        Index("ix_quiz_hands_session_number", "session_id", "hand_number"),
    )


class HandHistory(Base):
    __tablename__ = "hand_history"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("quiz_sessions.id", ondelete="SET NULL"), nullable=True
    )
    tournament_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    hand_number: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    hero_position: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    hero_hand: Mapped[str] = mapped_column(String(10), nullable=False)
    board: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    actions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    pot_size_bb: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    result_bb: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    gto_ev_bb: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    ev_diff_bb: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    played_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="hand_history")
    session: Mapped[Optional["QuizSession"]] = relationship()

    __table_args__ = (
        Index("ix_hand_history_user_played", "user_id", "played_at"),
    )


class ModelCheckpoint(Base):
    __tablename__ = "model_checkpoints"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_type: Mapped[ModelType] = mapped_column(nullable=False)
    config: Mapped[dict] = mapped_column(JSON, nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    iterations: Mapped[int] = mapped_column(Integer, nullable=False)
    exploitability_bb: Mapped[Optional[float]] = mapped_column(Numeric(10, 3), nullable=True)
    exploitability_trials: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    parent_checkpoint_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("model_checkpoints.id"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    parent: Mapped[Optional["ModelCheckpoint"]] = relationship(remote_side=[id])
    children: Mapped[list["ModelCheckpoint"]] = relationship(back_populates="parent")
    training_runs: Mapped[list["TrainingRun"]] = relationship(
        back_populates="checkpoint", cascade="all, delete-orphan"
    )
    exploitability_logs: Mapped[list["ExploitabilityLog"]] = relationship(
        back_populates="checkpoint", cascade="all, delete-orphan"
    )
    bookmarks: Mapped[list["UserModelBookmark"]] = relationship(
        back_populates="checkpoint", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("name", "iterations", name="uq_model_checkpoint_name_iter"),
        Index("ix_model_checkpoints_type_active", "model_type", "is_active"),
    )


class TrainingRun(Base):
    __tablename__ = "training_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    checkpoint_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("model_checkpoints.id", ondelete="CASCADE"), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    target_iterations: Mapped[int] = mapped_column(Integer, nullable=False)
    completed_iterations: Mapped[int] = mapped_column(Integer, default=0)
    iterations_per_second: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    final_exploitability_bb: Mapped[Optional[float]] = mapped_column(Numeric(10, 3), nullable=True)
    status: Mapped[TrainingStatus] = mapped_column(default=TrainingStatus.RUNNING)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    git_commit: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)

    checkpoint: Mapped["ModelCheckpoint"] = relationship(back_populates="training_runs")
    exploitability_logs: Mapped[list["ExploitabilityLog"]] = relationship(
        back_populates="training_run", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_training_runs_checkpoint_started", "checkpoint_id", "started_at"),
    )


class ExploitabilityLog(Base):
    __tablename__ = "exploitability_log"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    checkpoint_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("model_checkpoints.id", ondelete="CASCADE"), nullable=False
    )
    training_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("training_runs.id", ondelete="CASCADE"), nullable=True
    )
    iteration: Mapped[int] = mapped_column(Integer, nullable=False)
    exploitability_bb: Mapped[float] = mapped_column(Numeric(10, 3), nullable=False)
    br0_bb: Mapped[float] = mapped_column(Numeric(10, 3), nullable=False)
    br1_bb: Mapped[float] = mapped_column(Numeric(10, 3), nullable=False)
    trials: Mapped[int] = mapped_column(Integer, nullable=False)
    boards_per_trial: Mapped[int] = mapped_column(Integer, nullable=False)
    measured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    checkpoint: Mapped["ModelCheckpoint"] = relationship(back_populates="exploitability_logs")
    training_run: Mapped[Optional["TrainingRun"]] = relationship(back_populates="exploitability_logs")

    __table_args__ = (
        Index("ix_exploitability_checkpoint_iter", "checkpoint_id", "iteration"),
    )


class UserModelBookmark(Base):
    __tablename__ = "user_model_bookmarks"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    checkpoint_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("model_checkpoints.id", ondelete="CASCADE"), nullable=False
    )
    label: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="model_bookmarks")
    checkpoint: Mapped["ModelCheckpoint"] = relationship(back_populates="bookmarks")

    __table_args__ = (
        UniqueConstraint("user_id", "checkpoint_id", name="uq_user_model_bookmark"),
    )