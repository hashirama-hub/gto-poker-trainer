import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { QuizHand, QuizResult, QuizSession, User } from '@/types';

interface QuizState {
  currentHand: QuizHand | null;
  currentResult: QuizResult | null;
  session: QuizSession | null;
  history: QuizHand[];
  setCurrentHand: (hand: QuizHand | null) => void;
  setCurrentResult: (result: QuizResult | null) => void;
  setSession: (session: QuizSession | null) => void;
  addToHistory: (hand: QuizHand) => void;
  clearQuiz: () => void;
}

export const useQuizStore = create<QuizState>()(
  persist(
    (set) => ({
      currentHand: null,
      currentResult: null,
      session: null,
      history: [],
      setCurrentHand: (hand) => set({ currentHand: hand }),
      setCurrentResult: (result) => set({ currentResult: result }),
      setSession: (session) => set({ session }),
      addToHistory: (hand) => set((state) => ({ history: [...state.history, hand] })),
      clearQuiz: () => set({ currentHand: null, currentResult: null, session: null, history: [] }),
    }),
    { name: 'quiz-storage', partialize: (state) => ({ history: state.history }) }
  )
);

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (user: User, token: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      login: (user, token) => {
        if (typeof window !== 'undefined') localStorage.setItem('access_token', token);
        set({ user, token, isAuthenticated: true });
      },
      logout: () => {
        if (typeof window !== 'undefined') localStorage.removeItem('access_token');
        set({ user: null, token: null, isAuthenticated: false });
      },
    }),
    { name: 'auth-storage' }
  )
);

interface UISettings {
  theme: 'light' | 'dark' | 'system';
  soundEnabled: boolean;
  animationsEnabled: boolean;
  compactMode: boolean;
  setTheme: (theme: 'light' | 'dark' | 'system') => void;
  toggleSound: () => void;
  toggleAnimations: () => void;
  toggleCompact: () => void;
}

export const useUISettings = create<UISettings>()(
  persist(
    (set) => ({
      theme: 'system',
      soundEnabled: true,
      animationsEnabled: true,
      compactMode: false,
      setTheme: (theme) => {
        if (typeof window !== 'undefined') {
          const root = window.document.documentElement;
          root.classList.remove('light', 'dark');
          if (theme === 'system') {
            const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
            root.classList.add(systemTheme);
          } else {
            root.classList.add(theme);
          }
        }
        set({ theme });
      },
      toggleSound: () => set((state) => ({ soundEnabled: !state.soundEnabled })),
      toggleAnimations: () => set((state) => ({ animationsEnabled: !state.animationsEnabled })),
      toggleCompact: () => set((state) => ({ compactMode: !state.compactMode })),
    }),
    { name: 'ui-settings' }
  )
);

interface TrainingState {
  activeRun: TrainingRun | null;
  runs: TrainingRun[];
  setActiveRun: (run: TrainingRun | null) => void;
  setRuns: (runs: TrainingRun[]) => void;
  addRun: (run: TrainingRun) => void;
  updateRun: (id: string, updates: Partial<TrainingRun>) => void;
}

import type { TrainingRun } from '@/types';

export const useTrainingStore = create<TrainingState>((set) => ({
  activeRun: null,
  runs: [],
  setActiveRun: (run) => set({ activeRun: run }),
  setRuns: (runs) => set({ runs }),
  addRun: (run) => set((state) => ({ runs: [run, ...state.runs] })),
  updateRun: (id, updates) =>
    set((state) => ({
      runs: state.runs.map((r) => (r.id === id ? { ...r, ...updates } : r)),
      activeRun: state.activeRun?.id === id ? { ...state.activeRun, ...updates } : state.activeRun,
    })),
}));