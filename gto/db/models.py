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


class Tournament(Base):
    __tablename__ = "tournaments"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[TournamentStatus] = mapped_column(Enum(TournamentStatus), default=TournamentStatus.REGISTERING, index=True)
    max_players: Mapped[int] = mapped_column(Integer, default=90)
    players_per_table: Mapped[int] = mapped_column(Integer, default=9)
    starting_stack: Mapped[int] = mapped_column(Integer, default=10000)  # in chips
    level_duration_minutes: Mapped[int] = mapped_column(Integer, default=10)
    current_level: Mapped[int] = mapped_column(Integer, default=0)
    small_blind: Mapped[int] = mapped_column(Integer, default=50)
    big_blind: Mapped[int] = mapped_column(Integer, default=100)
    ante: Mapped[int] = mapped_column(Integer, default=0)
    payout_structure: Mapped[list[float]] = mapped_column(JSON, nullable=False, default=[])  # percentages
    total_prize_pool: Mapped[int] = mapped_column(Integer, default=0)
    buy_in: Mapped[int] = mapped_column(Integer, default=0)
    rake: Mapped[int] = mapped_column(Integer, default=0)
    real_time_mode: Mapped[bool] = mapped_column(default=True)  # False = turn-based
    action_timer_seconds: Mapped[int] = mapped_column(Integer, default=30)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default={})

    tables: Mapped[list["Table"]] = relationship(back_populates="tournament", cascade="all, delete-orphan")
    players: Mapped[list["TournamentPlayer"]] = relationship(back_populates="tournament", cascade="all, delete-orphan")


class Table(Base):
    __tablename__ = "tables"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tournament_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tournaments.id"), nullable=False, index=True)
    table_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[TableStatus] = mapped_column(Enum(TableStatus), default=TableStatus.WAITING, index=True)
    max_seats: Mapped[int] = mapped_column(Integer, default=9)
    button_seat: Mapped[int] = mapped_column(Integer, default=0)
    current_hand_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    hand_number: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tournament: Mapped["Tournament"] = relationship(back_populates="tables")
    seats: Mapped[list["TableSeat"]] = relationship(back_populates="table", cascade="all, delete-orphan")
    hands: Mapped[list["TableHand"]] = relationship(back_populates="table", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("tournament_id", "table_number", name="uq_tournament_table"),)


class TableSeat(Base):
    __tablename__ = "table_seats"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    table_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tables.id"), nullable=False, index=True)
    seat_number: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-8 for 9-max
    player_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("tournament_players.id"), nullable=True, index=True)
    stack: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(default=True)
    is_sitting_out: Mapped[bool] = mapped_column(default=False)
    position: Mapped[str | None] = mapped_column(String(10), nullable=True)  # BTN, SB, BB, UTG, etc.
    last_action: Mapped[str | None] = mapped_column(String(20), nullable=True)
    last_action_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    acted_this_street: Mapped[bool] = mapped_column(default=False)
    is_all_in: Mapped[bool] = mapped_column(default=False)
    hole_cards: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)  # card indices 0-51
    current_bet: Mapped[int] = mapped_column(Integer, default=0)
    total_bet_this_hand: Mapped[int] = mapped_column(Integer, default=0)

    table: Mapped["Table"] = relationship(back_populates="seats")
    player: Mapped["TournamentPlayer | None"] = relationship()

    __table_args__ = (UniqueConstraint("table_id", "seat_number", name="uq_table_seat"),)


class TournamentPlayer(Base):
    __tablename__ = "tournament_players"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tournament_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tournaments.id"), nullable=False, index=True)
    user_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    username: Mapped[str] = mapped_column(String(50), nullable=False)
    is_bot: Mapped[bool] = mapped_column(default=False)
    bot_difficulty: Mapped[str | None] = mapped_column(String(20), nullable=True)  # "gto", "exploitative", etc.
    starting_stack: Mapped[int] = mapped_column(Integer, default=10000)
    current_stack: Mapped[int] = mapped_column(Integer, default=10000)
    total_winnings: Mapped[int] = mapped_column(Integer, default=0)
    finish_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prize_won: Mapped[int] = mapped_column(Integer, default=0)
    is_eliminated: Mapped[bool] = mapped_column(default=False)
    eliminated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    eliminated_hand: Mapped[int | None] = mapped_column(Integer, nullable=True)
    registered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    seated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    current_table_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("tables.id"), nullable=True)
    current_seat_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("table_seats.id"), nullable=True)

    tournament: Mapped["Tournament"] = relationship(back_populates="players")
    user: Mapped["User | None"] = relationship()
    current_table: Mapped["Table | None"] = relationship()
    current_seat: Mapped["TableSeat | None"] = relationship()


class TableHand(Base):
    __tablename__ = "table_hands"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    table_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tables.id"), nullable=False, index=True)
    hand_number: Mapped[int] = mapped_column(Integer, nullable=False)
    tournament_level: Mapped[int] = mapped_column(Integer, nullable=False)
    small_blind: Mapped[int] = mapped_column(Integer, nullable=False)
    big_blind: Mapped[int] = mapped_column(Integer, nullable=False)
    ante: Mapped[int] = mapped_column(Integer, default=0)
    button_seat: Mapped[int] = mapped_column(Integer, nullable=False)
    sb_seat: Mapped[int] = mapped_column(Integer, nullable=False)
    bb_seat: Mapped[int] = mapped_column(Integer, nullable=False)
    board: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=[])
    pot: Mapped[int] = mapped_column(Integer, default=0)
    street: Mapped[Street] = mapped_column(Enum(Street), default=Street.PREFLOP)
    current_bet: Mapped[int] = mapped_column(Integer, default=0)
    min_raise: Mapped[int] = mapped_column(Integer, default=0)
    last_raiser_seat: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_aggressor_seat: Mapped[int | None] = mapped_column(Integer, nullable=True)
    seats_in_hand: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=[])
    active_seat: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    winner_seats: Mapped[list[int]] = mapped_column(JSON, nullable=True)
    win_amounts: Mapped[list[int]] = mapped_column(JSON, nullable=True)
    hand_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # for showdown
    gto_analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # EV analysis per seat

    table: Mapped["Table"] = relationship(back_populates="hands")
    actions: Mapped[list["HandAction"]] = relationship(back_populates="hand", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("table_id", "hand_number", name="uq_table_hand"),)


class HandAction(Base):
    __tablename__ = "hand_actions"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    hand_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("table_hands.id"), nullable=False, index=True)
    seat_number: Mapped[int] = mapped_column(Integer, nullable=False)
    street: Mapped[Street] = mapped_column(Enum(Street), nullable=False)
    action_type: Mapped[ActionType] = mapped_column(Enum(ActionType), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, default=0)
    pot_after: Mapped[int] = mapped_column(Integer, default=0)
    stack_after: Mapped[int] = mapped_column(Integer, default=0)
    is_gto_action: Mapped[bool] = mapped_column(default=False)
    gto_ev_bb: Mapped[float | None] = mapped_column(Float, nullable=True)
    action_index: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    hand: Mapped["TableHand"] = relationship(back_populates="actions")