-- GTO Poker Trainer - PostgreSQL Schema
-- Run: psql -U postgres -d poker_trainer -f db/schema.sql

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    elo_rating INTEGER DEFAULT 1000,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Quiz sessions (training history)
CREATE TABLE IF NOT EXISTS quiz_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    mode VARCHAR(20) NOT NULL, -- 'pushfold', 'icm', 'preflop', 'flop'
    hands_total INTEGER NOT NULL,
    hands_answered INTEGER NOT NULL,
    avg_score DECIMAL(5,2),
    duration_seconds INTEGER,
    config JSONB, -- store quiz parameters
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Individual hand questions within a session
CREATE TABLE IF NOT EXISTS quiz_hands (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES quiz_sessions(id) ON DELETE CASCADE,
    hand_number INTEGER NOT NULL,
    hero_position INTEGER NOT NULL, -- 0=SB, 1=BB
    hand_name VARCHAR(10) NOT NULL, -- e.g. 'AA', '72o', 'A5s'
    board_cards VARCHAR(50), -- flop/turn/river cards if applicable
    actions JSONB NOT NULL, -- [{"label": "fold", "gto_pct": 0.0, "ev_bb": -0.5}, ...]
    user_choice VARCHAR(20),
    user_ev_bb DECIMAL(8,3),
    gto_best_action VARCHAR(20),
    score INTEGER, -- 0-100
    time_taken_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Hand history for review (imported or played)
CREATE TABLE IF NOT EXISTS hand_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    session_id UUID REFERENCES quiz_sessions(id) ON DELETE SET NULL,
    tournament_id VARCHAR(100), -- external tournament ID
    hand_number BIGINT,
    hero_position VARCHAR(10), -- 'SB', 'BB', 'BTN', 'CO', etc.
    hero_hand VARCHAR(10),
    board TEXT, -- JSON array of cards
    actions TEXT, -- JSON action sequence
    pot_size_bb DECIMAL(10,2),
    result_bb DECIMAL(10,2), -- net result in bb
    gto_ev_bb DECIMAL(10,2), -- GTO EV for hero's line
    ev_diff_bb DECIMAL(10,2), -- actual - GTO
    played_at TIMESTAMP WITH TIME ZONE,
    imported_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Model checkpoints metadata
CREATE TABLE IF NOT EXISTS model_checkpoints (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL, -- 'pushfold_15bb', 'full100_sb_bb'
    model_type VARCHAR(30) NOT NULL, -- 'pushfold', 'full100', 'icm', 'flop_subgame'
    config JSONB NOT NULL, -- GameConfig + SolverConfig as JSON
    file_path VARCHAR(500) NOT NULL,
    file_size_bytes BIGINT,
    iterations INTEGER NOT NULL,
    exploitability_bb DECIMAL(10,3),
    exploitability_trials INTEGER,
    parent_checkpoint_id UUID REFERENCES model_checkpoints(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(name, iterations)
);

-- Training runs (solver iterations)
CREATE TABLE IF NOT EXISTS training_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    checkpoint_id UUID REFERENCES model_checkpoints(id) ON DELETE CASCADE,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    target_iterations INTEGER,
    completed_iterations INTEGER DEFAULT 0,
    iterations_per_second DECIMAL(10,2),
    final_exploitability_bb DECIMAL(10,3),
    status VARCHAR(20) DEFAULT 'running', -- 'running', 'completed', 'stopped', 'failed'
    error_message TEXT,
    git_commit VARCHAR(40)
);

-- Exploitability measurements over time
CREATE TABLE IF NOT EXISTS exploitability_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    checkpoint_id UUID REFERENCES model_checkpoints(id) ON DELETE CASCADE,
    training_run_id UUID REFERENCES training_runs(id) ON DELETE CASCADE,
    iteration INTEGER NOT NULL,
    exploitability_bb DECIMAL(10,3),
    br0_bb DECIMAL(10,3),
    br1_bb DECIMAL(10,3),
    trials INTEGER,
    boards_per_trial INTEGER,
    measured_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User model preferences / bookmarks
CREATE TABLE IF NOT EXISTS user_model_bookmarks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    checkpoint_id UUID REFERENCES model_checkpoints(id) ON DELETE CASCADE,
    label VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, checkpoint_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_quiz_sessions_user_created ON quiz_sessions(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_quiz_hands_session ON quiz_hands(session_id, hand_number);
CREATE INDEX IF NOT EXISTS idx_hand_history_user_played ON hand_history(user_id, played_at DESC);
CREATE INDEX IF NOT EXISTS idx_model_checkpoints_type ON model_checkpoints(model_type, is_active);
CREATE INDEX IF NOT EXISTS idx_training_runs_checkpoint ON training_runs(checkpoint_id, started_at);
CREATE INDEX IF NOT EXISTS idx_exploitability_checkpoint_iter ON exploitability_log(checkpoint_id, iteration);

-- Updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();