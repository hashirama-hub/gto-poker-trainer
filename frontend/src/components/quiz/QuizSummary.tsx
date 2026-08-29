'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { HandMatrix } from '@/components/ui/HandMatrix';
import { cn, formatNumber, scoreToColor, verdictToColor, handToDisplay, getHandMatrixPosition, RANKS } from '@/lib/utils';
import type { QuizSession, QuizHand, QuizResult } from '@/types';
import { Trophy, Target, TrendingUp, ArrowLeft, Download, Share2, RotateCcw } from 'lucide-react';
import { useQuizStore } from '@/lib/store';

interface QuizSummaryProps {
  session: QuizSession;
  hands: (QuizHand & { result?: QuizResult })[];
  onRestart: () => void;
  onNewQuiz: () => void;
}

export function QuizSummary({ session, hands, onRestart, onNewQuiz }: QuizSummaryProps) {
  const answeredHands = hands.filter((h) => h.result);
  const scores = answeredHands.map((h) => h.result!.score);
  const avgScore = scores.length ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : 0;
  const gtoCount = scores.filter((s) => s >= 90).length;
  const okCount = scores.filter((s) => s >= 70 && s < 90).length;
  const terribleCount = scores.filter((s) => s < 70).length;

  const bestHand = answeredHands.reduce((best, curr) => (curr.result!.score > best.result!.score ? curr : best), answeredHands[0]);
  const worstHand = answeredHands.reduce((worst, curr) => (curr.result!.score < worst.result!.score ? curr : worst), answeredHands[0]);

  const evDiffs = answeredHands.map((h) => h.result!.best_ev_bb - h.result!.user_ev_bb);
  const totalEvLoss = evDiffs.reduce((a, b) => a + b, 0);
  const avgEvLoss = evDiffs.length ? totalEvLoss / evDiffs.length : 0;

  const actionStats: Record<string, { count: number; correct: number; totalEv: number }> = {};
  answeredHands.forEach((h) => {
    const action = h.result!.gto_best;
    if (!actionStats[action]) actionStats[action] = { count: 0, correct: 0, totalEv: 0 };
    actionStats[action].count++;
    if (h.result!.verdict === 'GTO') actionStats[action].correct++;
    actionStats[action].totalEv += h.result!.user_ev_bb;
  });

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-dark-900 dark:text-dark-100">Session Complete</h1>
          <p className="text-dark-500 dark:text-dark-400 mt-1">
            {session.mode} • {answeredHands.length}/{session.hands_total} hands • {Math.round(session.duration_seconds / 60)} min
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={onNewQuiz} className="gap-2">
            <RotateCcw className="w-4 h-4" />
            New Quiz
          </Button>
          <Button variant="outline" onClick={onRestart} className="gap-2">
            <ArrowLeft className="w-4 h-4" />
            Same Settings
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card variant="elevated" className="text-center">
          <CardContent className="py-4">
            <div className={cn('text-4xl font-bold', scoreToColor(avgScore))}>{avgScore}</div>
            <div className="text-dark-500 dark:text-dark-400 text-sm mt-1">Average Score</div>
            <div className="w-24 h-2 mx-auto mt-2 bg-dark-200 dark:bg-dark-700 rounded-full overflow-hidden">
              <div
                className={cn('h-full rounded-full transition-all duration-1000', scoreToColor(avgScore).split(' ')[0].replace('text-', 'bg-'))}
                style={{ width: `${avgScore}%` }}
              />
            </div>
          </CardContent>
        </Card>

        <Card variant="outlined">
          <CardContent className="py-4 text-center">
            <div className="flex items-center justify-center gap-1 mb-1">
              <Trophy className="w-5 h-5 text-yellow-500" />
              <span className="text-xl font-bold text-green-600 dark:text-green-400">{gtoCount}</span>
            </div>
            <div className="text-dark-500 dark:text-dark-400 text-sm">GTO (≥90)</div>
            <div className="text-xs text-dark-400 dark:text-dark-500">{answeredHands.length ? Math.round((gtoCount / answeredHands.length) * 100) : 0}%</div>
          </CardContent>
        </Card>

        <Card variant="outlined">
          <CardContent className="py-4 text-center">
            <div className="flex items-center justify-center gap-1 mb-1">
              <Target className="w-5 h-5 text-blue-500" />
              <span className="text-xl font-bold text-blue-600 dark:text-blue-400">{okCount}</span>
            </div>
            <div className="text-dark-500 dark:text-dark-400 text-sm">Close (70-89)</div>
            <div className="text-xs text-dark-400 dark:text-dark-500">{answeredHands.length ? Math.round((okCount / answeredHands.length) * 100) : 0}%</div>
          </CardContent>
        </Card>

        <Card variant="outlined">
          <CardContent className="py-4 text-center">
            <div className="flex items-center justify-center gap-1 mb-1">
              <TrendingUp className="w-5 h-5 text-red-500" />
              <span className="text-xl font-bold text-red-600 dark:text-red-400">
                {avgEvLoss >= 0 ? '+' : ''}{avgEvLoss.toFixed(2)}
              </span>
            </div>
            <div className="text-dark-500 dark:text-dark-400 text-sm">Avg EV Loss (bb)</div>
            <div className="text-xs text-dark-400 dark:text-dark-500">Total: {totalEvLoss >= 0 ? '+' : ''}{totalEvLoss.toFixed(2)}bb</div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card variant="outlined">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="w-5 h-5" />
              Best & Worst Decisions
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {bestHand && bestHand.result && (
              <div className="p-3 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-semibold text-green-700 dark:text-green-300">
                    {handToDisplay(bestHand.hand)} — {bestHand.result.score}/100
                  </span>
                  <span className={cn('px-2 py-0.5 rounded text-xs font-medium', verdictToColor(bestHand.result.verdict))}>
                    {bestHand.result.verdict}
                  </span>
                </div>
                <div className="text-sm text-dark-600 dark:text-dark-300">
                  You: <strong>{bestHand.result.gto_best}</strong> (EV: {bestHand.result.user_ev_bb >= 0 ? '+' : ''}{bestHand.result.user_ev_bb.toFixed(2)}bb)
                </div>
              </div>
            )}
            {worstHand && worstHand.result && (
              <div className="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-semibold text-red-700 dark:text-red-300">
                    {handToDisplay(worstHand.hand)} — {worstHand.result.score}/100
                  </span>
                  <span className={cn('px-2 py-0.5 rounded text-xs font-medium', verdictToColor(worstHand.result.verdict))}>
                    {worstHand.result.verdict}
                  </span>
                </div>
                <div className="text-sm text-dark-600 dark:text-dark-300">
                  You: <strong>{worstHand.result.gto_best === worstHand.result.gto_best ? 'GTO' : worstHand.result.gto_best}</strong> — GTO: <strong>{worstHand.result.gto_best}</strong> (EV: {worstHand.result.best_ev_bb >= 0 ? '+' : ''}{worstHand.result.best_ev_bb.toFixed(2)}bb)
                  <br />
                  Your EV: {worstHand.result.user_ev_bb >= 0 ? '+' : ''}{worstHand.result.user_ev_bb.toFixed(2)}bb (Loss: {(worstHand.result.best_ev_bb - worstHand.result.user_ev_bb).toFixed(2)}bb)
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card variant="outlined">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5" />
              Action Frequency Analysis
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {Object.entries(actionStats)
              .sort(([, a], [, b]) => b.count - a.count)
              .map(([action, stats]) => (
                <div key={action} className="p-3 rounded-lg bg-dark-50 dark:bg-dark-800/50">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-medium capitalize">{action}</span>
                    <span className="text-sm text-dark-500 dark:text-dark-400">
                      {stats.count}× ({Math.round((stats.count / answeredHands.length) * 100)}%)
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <div className="flex-1 h-2 bg-dark-200 dark:bg-dark-700 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-green-500 rounded-full transition-all duration-500"
                        style={{ width: `${stats.count ? (stats.correct / stats.count) * 100 : 0}%` }}
                      />
                    </div>
                    <span className="text-green-600 dark:text-green-400 font-mono text-xs">
                      {stats.count ? Math.round((stats.correct / stats.count) * 100) : 0}% GTO
                    </span>
                    <span className="text-dark-500 dark:text-dark-400 font-mono text-xs">
                      Avg EV: {stats.count ? (stats.totalEv / stats.count).toFixed(2) : 0}bb
                    </span>
                  </div>
                </div>
              ))}
          </CardContent>
        </Card>
      </div>

      <Card variant="outlined">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Target className="w-5 h-5" />
            GTO Range Summary
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="mb-4">
            <HandMatrix
              highlights={answeredHands.reduce((acc, h) => {
                if (h.result) {
                  const action = h.result.gto_best;
                  let color = '#64748b';
                  if (action.toLowerCase().includes('raise') || action.toLowerCase().includes('shove') || action.toLowerCase().includes('bet')) {
                    color = '#ef4444';
                  } else if (action.toLowerCase().includes('call')) {
                    color = '#22c55e';
                  } else if (action.toLowerCase().includes('fold')) {
                    color = '#64748b';
                  } else if (action.toLowerCase().includes('check')) {
                    color = '#3b82f6';
                  }
                  acc[h.hand] = { color, label: `${h.result.gto_pct.toFixed(0)}%` };
                }
                return acc;
              }, {} as Record<string, { color: string; label?: string }>)}
              cellSize={28}
            />
          </div>
        </CardContent>
      </Card>

      <div className="flex gap-4 justify-center">
        <Button variant="primary" size="lg" onClick={onRestart} className="gap-2">
          <RotateCcw className="w-5 h-5" />
          Play Again (Same Settings)
        </Button>
        <Button variant="outline" size="lg" onClick={onNewQuiz} className="gap-2">
          <ArrowLeft className="w-5 h-5" />
          Change Mode
        </Button>
      </div>
    </div>
  );
}