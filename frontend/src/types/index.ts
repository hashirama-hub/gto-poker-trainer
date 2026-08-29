export interface QuizAction {
  label: string;
  gto_pct: number;
  ev_bb: number;
}

export interface QuizHand {
  id: string;
  hand_number: number;
  hero_position: number;
  hand_name: string;
  board_cards: string | null;
  actions: QuizAction[];
  prompt: string;
}

export interface QuizResult {
  score: number;
  verdict: 'GTO' | 'ok' | 'terrible';
  gto_best: string;
  gto_pct: number;
  user_ev_bb: number;
  best_ev_bb: number;
  worst_ev_bb: number;
}

export interface QuizSession {
  id: string;
  mode: 'pushfold' | 'icm' | 'preflop' | 'flop';
  hands_total: number;
  hands_answered: number;
  avg_score: number | null;
  duration_seconds: number | null;
  created_at: string;
}

export interface GTOActionInfo {
  label: string;
  gto_pct: number;
  ev_bb: number;
}

export interface GTOHandInfo {
  hand: string;
  position: 'SB' | 'BB';
  effective_bb: number;
  actions: GTOActionInfo[];
}

export interface GTOInfoResponse {
  model_type: string;
  hands: GTOHandInfo[];
}

export interface ModelCheckpoint {
  id: string;
  name: string;
  model_type: string;
  config: Record<string, unknown>;
  file_path: string;
  file_size_bytes: number | null;
  iterations: number;
  exploitability_bb: number | null;
  exploitability_trials: number | null;
  parent_checkpoint_id: string | null;
  is_active: boolean;
  created_at: string;
}

export interface TrainingRun {
  id: string;
  checkpoint_id: string;
  started_at: string;
  completed_at: string | null;
  target_iterations: number;
  completed_iterations: number;
  iterations_per_second: number | null;
  final_exploitability_bb: number | null;
  status: 'running' | 'completed' | 'failed';
  error_message: string | null;
  git_commit: string | null;
}

export interface HandHistory {
  id: string;
  user_id: string;
  tournament_id: string | null;
  hand_number: number | null;
  hero_position: string | null;
  hero_hand: string;
  board: string[] | null;
  actions: Record<string, unknown>[] | null;
  pot_size_bb: number | null;
  result_bb: number | null;
  gto_ev_bb: number | null;
  played_at: string | null;
  ev_diff_bb: number | null;
  imported_at: string;
}

export interface User {
  id: string;
  username: string;
  email: string | null;
  elo_rating: number;
  created_at: string;
}