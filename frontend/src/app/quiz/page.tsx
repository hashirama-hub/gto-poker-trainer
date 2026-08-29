'use client';

import { useState, useEffect, useCallback } from 'react';
import { QuizSetup } from '@/components/quiz/QuizSetup';
import { QuizQuestion } from '@/components/quiz/QuizQuestion';
import { QuizSummary } from '@/components/quiz/QuizSummary';
import { Button } from '@/components/ui/Button';
import { Card, CardContent } from '@/components/ui/Card';
import { useQuizStore } from '@/lib/store';
import { quizApi } from '@/lib/api';
import { Loader2, X, RotateCcw } from 'lucide-react';

export default function QuizPage() {
  const { currentHand, currentResult, session, history, setCurrentHand, setCurrentResult, setSession, addToHistory, clearQuiz } = useQuizStore();
  const [phase, setPhase] = useState<'setup' | 'playing' | 'summary'>('setup');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startQuiz = useCallback(async (mode: string, hands: number, config: Record<string, unknown>) => {
    setLoading(true);
    setError(null);
    clearQuiz();
    try {
      const res = await quizApi.start(mode, hands, config);
      setCurrentHand(res.data);
      setSession({ ...res.data, mode, hands_total: hands, hands_answered: 0, avg_score: null, duration_seconds: null, created_at: new Date().toISOString() });
      setPhase('playing');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to start quiz';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [setCurrentHand, setSession, clearQuiz]);

  const submitAnswer = useCallback(async (choice: string) => {
    if (!session || !currentHand) return;
    setLoading(true);
    try {
      const res = await quizApi.submit(session.id, currentHand.id, choice);
      setCurrentResult(res.data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to submit');
    } finally {
      setLoading(false);
    }
  }, [session, currentHand, setCurrentResult]);

  const nextQuestion = useCallback(async () => {
    if (!session) return;
    setLoading(true);
    try {
      const res = await quizApi.next(session.id);
      setCurrentHand(res.data);
      setCurrentResult(null);
    } catch (err: unknown) {
      if (err instanceof Error && err.message.includes('completed')) {
        const summary = await quizApi.summary(session.id);
        setPhase('summary');
      } else {
        setError(err instanceof Error ? err.message : 'Failed to get next question');
      }
    } finally {
      setLoading(false);
    }
  }, [session, setCurrentHand, setCurrentResult]);

  const handleRestart = useCallback(() => {
    if (!session) return;
    setPhase('playing');
    startQuiz(session.mode, session.hands_total, {});
  }, [session, startQuiz]);

  const handleNewQuiz = useCallback(() => {
    setPhase('setup');
    clearQuiz();
  }, [clearQuiz]);

  if (phase === 'setup') {
    return <QuizSetup onStart={startQuiz} />;
  }

  if (phase === 'summary') {
    return (
      <QuizSummary
        session={session!}
        hands={history.map((h) => ({ ...h, result: currentResult }))}
        onRestart={handleRestart}
        onNewQuiz={handleNewQuiz}
      />
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={handleNewQuiz} disabled={loading}>
            <X className="w-4 h-4" />
          </Button>
          <div>
            <p className="font-semibold text-dark-900 dark:text-dark-100">
              {session?.mode?.toUpperCase()} — Hand {session?.hands_answered + 1}/{session?.hands_total}
            </p>
            <p className="text-sm text-dark-500 dark:text-dark-400">
              {currentHand?.hand} • {currentHand?.hero_position === 0 ? 'SB' : 'BB'}
            </p>
          </div>
        </div>
        {loading && <Loader2 className="w-5 h-5 animate-spin text-primary-600" />}
      </div>

      {error && (
        <Card variant="outlined" className="border-red-300 dark:border-red-800 bg-red-50 dark:bg-red-900/20">
          <CardContent className="flex items-center justify-between p-3">
            <span className="text-red-700 dark:text-red-300">{error}</span>
            <Button variant="ghost" size="sm" onClick={() => setError(null)}>
              <X className="w-4 h-4" />
            </Button>
          </CardContent>
        </Card>
      )}

      {currentHand && (
        <QuizQuestion
          question={currentHand}
          result={currentResult || undefined}
          onAnswer={submitAnswer}
          handNumber={session?.hands_answered + 1 || 1}
          totalHands={session?.hands_total || 10}
          isLoading={loading}
        />
      )}

      {currentResult && !loading && (
        <Button
          size="lg"
          className="w-full"
          onClick={nextQuestion}
          variant={currentResult.verdict === 'GTO' ? 'primary' : currentResult.verdict === 'terrible' ? 'danger' : 'secondary'}
        >
          {currentResult.verdict === 'GTO' ? '🏆 Perfect! Next →' : currentResult.verdict === 'terrible' ? '💥 Review & Next →' : '✓ Good, Next →'}
        </Button>
      )}
    </div>
  );
}