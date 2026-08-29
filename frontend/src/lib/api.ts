import axios from 'axios';
import type { QuizHand, QuizResult, QuizSession, GTOInfoResponse, GTOHandInfo, ModelCheckpoint, TrainingRun, HandHistory, User } from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
});

api.interceptors.request.use((config) => {
  const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      if (typeof window !== 'undefined') {
        localStorage.removeItem('access_token');
        window.location.href = '/login';
      }
    }
    return Promise.reject(err);
  }
);

export const quizApi = {
  start: (mode: string, hands: number, config: Record<string, unknown>) =>
    api.post<QuizHand>('/quiz/start', { mode, hands, config }),
  submit: (sessionId: string, handId: string, choice: string) =>
    api.post<QuizResult>(`/quiz/${sessionId}/submit`, { hand_id: handId, choice }),
  next: (sessionId: string) =>
    api.get<QuizHand>(`/quiz/${sessionId}/next`),
  summary: (sessionId: string) =>
    api.get<QuizSession>(`/quiz/${sessionId}/summary`),
};

export const gtoApi = {
  info: (hands: string[], depth?: number, modelPath?: string) =>
    api.post<GTOInfoResponse>('/gto/info', { hands, depth, model_path: modelPath }),
  listModels: (type?: string) =>
    api.get<ModelCheckpoint[]>('/gto/models', { params: { model_type: type } }),
  createModel: (data: Partial<ModelCheckpoint>) =>
    api.post<ModelCheckpoint>('/gto/models', data),
};

export const trainingApi = {
  listRuns: (checkpointId?: string) =>
    api.get<TrainingRun[]>('/gto/training', { params: { checkpoint_id: checkpointId } }),
  startRun: (checkpointId: string, targetIterations: number) =>
    api.post<TrainingRun>('/gto/training', { checkpoint_id: checkpointId, target_iterations: targetIterations }),
};

export const handsApi = {
  list: (page = 1, limit = 50) =>
    api.get<HandHistory[]>('/hands', { params: { page, limit } }),
  create: (data: Partial<HandHistory>) =>
    api.post<HandHistory>('/hands', data),
  import: (file: File) => {
    const form = new FormData();
    form.append('file', file);
    return api.post<{ imported: number }>('/hands/import', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
};

export const authApi = {
  login: (username: string, password: string) =>
    api.post<{ access_token: string; token_type: string; user: User }>('/auth/login', { username, password }),
  register: (username: string, email: string, password: string) =>
    api.post<User>('/auth/register', { username, email, password }),
  me: () => api.get<User>('/auth/me'),
};

export default api;