'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { ActionButton } from '@/components/ui/ActionButton';
import { HandMatrix } from '@/components/ui/HandMatrix';
import { cn, formatHand, handToDisplay, scoreToColor, verdictToColor } from '@/lib/utils';
import type { QuizHand, QuizResult } from '@/types';
import { useQuizStore } from '@/lib/store';
import { useState } from 'react';
import { CheckCircle, XCircle, AlertCircle, Trophy, Target } from 'lucide-react';

interface QuizQuestionProps {
  question: QuizHand;
  result?: QuizResult;
  onAnswer: (choice: string) => void;
  handNumber: number;
  totalHands: number;
  isLoading?: boolean;
}

export function QuizQuestion({
  question,
  result,
  onAnswer,
  handNumber,
  totalHands,
  isLoading = false,
}: QuizQuestionProps) {
  const { setCurrentResult } = useQuizStore();
  const [showMatrix, setShowMatrix] = useState(false);
  const [highlightedHand, setHighlightedHand] = useState<string | null>(null);

  const isAnswered = !!result;
  const userChoice = result?.gto_best ? (result.user_ev_bb === result.best_ev_bb ? result.gto_best : null) : null;

  const handleActionClick = (choice: string) => {
    if (!isAnswered && !isLoading) {
      onAnswer(choice);
    }
  };

  const getHighlights = () => {
    if (!result) return {};

    const highlights: Record<string, { color: string; label?: string }> = {};
    const actions = question.actions;

    actions.forEach((action) => {
      const freq = action.gto_pct / 100;
      if (freq > 0.01) {
        let color = '#64748b';
        if (action.label.toLowerCase().includes('raise') || action.label.toLowerCase().includes('shove') || action.label.toLowerCase().includes('bet')) {
          color = `rgba(220, 38, 38, ${0.3 + freq * 0.7})`;
        } else if (action.label.toLowerCase().includes('call')) {
          color = `rgba(34, 197, 94, ${0.3 + freq * 0.7})`;
        } else if (action.label.toLowerCase().includes('fold')) {
          color = `rgba(100, 116, 139, ${0.3 + freq * 0.7})`;
        } else if (action.label.toLowerCase().includes('check')) {
          color = `rgba(59, 130, 246, ${0.3 + freq * 0.7})`;
        }
        highlights[question.hand] = { color, label: `${action.gto_pct.toFixed(0)}%` };
      }
    });

    return highlights;
  };

  return (
    <div className="space-y-4">
      <Card variant="outlined" className={cn('transition-all', isAnswered && 'ring-2', result?.verdict === 'GTO' && 'ring-green-500', result?.verdict === 'terrible' && 'ring-red-500', result?.verdict === 'ok' && 'ring-yellow-500')}>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className={cn('px-3 py-1 rounded-full text-sm font-medium', scoreToColor(result?.score || 0))}>
                {isAnswered ? `Score: ${result?.score}/100` : `Question ${handNumber}/${totalHands}`}
              </span>
              {isAnswered && (
                <span className={cn('px-3 py-1 rounded-full text-sm font-medium', verdictToColor(result?.verdict || ''))}>
                  {result?.verdict === 'GTO' && <Trophy className="inline w-4 h-4 mr-1" />}
                  {result?.verdict === 'ok' && <CheckCircle className="inline w-4 h-4 mr-1" />}
                  {result?.verdict === 'terrible' && <XCircle className="inline w-4 h-4 mr-1" />}
                  {result?.verdict}
                </span>
              )}
            </div>
            <div className="flex items-center gap-2 text-dark-500 dark:text-dark-400 text-sm">
              <Target className="w-4 h-4" />
              <span>{question.hand}</span>
              {question.board_cards && (
                <>
                  <span>|</span>
                  <span className="font-mono">{question.board_cards}</span>
                </>
              )}
            </div>
          </div>
          <p className="text-dark-600 dark:text-dark-300 mt-2">{question.prompt}</p>
        </CardHeader>

        <CardContent className="space-y-4">
          <div className="grid gap-3 md:grid-cols-2">
            {question.actions.map((action) => (
              <ActionButton
                key={action.label}
                action={action}
                isSelected={isAnswered && action.label === (result?.gto_best || '') && result?.verdict === 'GTO'}
                isCorrect={isAnswered && action.label === result?.gto_best}
                isGtoBest={action.label === result?.gto_best}
                onClick={() => handleActionClick(action.label)}
                disabled={isAnswered || isLoading}
              />
            ))}
          </div>

          {!isAnswered && (
            <Button
              variant="ghost"
              size="sm"
              className="w-full justify-center"
              onClick={() => setShowMatrix(!showMatrix)}
            >
              {showMatrix ? 'Hide Range' : 'Show GTO Range'} Matrix
            </Button>
          )}

          {showMatrix && (
            <div className="animate-fade-in">
              <HandMatrix
                highlights={getHighlights()}
                cellSize={32}
                onClick={() => {}}
              />
            </div>
          )}

          {isAnswered && result && (
            <div className="space-y-3 pt-3 border-t border-dark-200 dark:border-dark-700">
              <div className="flex items-center gap-3 p-3 rounded-lg bg-dark-50 dark:bg-dark-800/50">
                <div className={cn('px-3 py-1 rounded-full text-sm font-medium', verdictToColor(result.verdict))}>
                  {result.verdict === 'GTO' && <Trophy className="inline w-4 h-4 mr-1" />}
                  {result.verdict === 'ok' && <CheckCircle className="inline w-4 h-4 mr-1" />}
                  {result.verdict === 'terrible' && <AlertCircle className="inline w-4 h-4 mr-1" />}
                  {result.verdict}
                </div>
                <div className="flex-1 text-sm text-dark-600 dark:text-dark-300">
                  GTO plays <strong>{result.gto_best}</strong> {result.gto_pct.toFixed(0)}% of the time
                  (EV: {result.best_ev_bb >= 0 ? '+' : ''}{result.best_ev_bb.toFixed(2)}bb)
                </div>
              </div>

              <div className="grid gap-2 sm:grid-cols-3 text-sm">
                <div className="p-2 rounded bg-green-50 dark:bg-green-900/20">
                  <div className="text-green-700 dark:text-green-300 font-medium">Best EV</div>
                  <div className="font-mono text-green-600 dark:text-green-400">
                    {result.best_ev_bb >= 0 ? '+' : ''}{result.best_ev_bb.toFixed(2)}bb
                  </div>
                </div>
                <div className="p-2 rounded bg-blue-50 dark:bg-blue-900/20">
                  <div className="text-blue-700 dark:text-blue-300 font-medium">Your EV</div>
                  <div className={cn('font-mono', result.user_ev_bb >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400')}>
                    {result.user_ev_bb >= 0 ? '+' : ''}{result.user_ev_bb.toFixed(2)}bb
                  </div>
                </div>
                <div className="p-2 rounded bg-red-50 dark:bg-red-900/20">
                  <div className="text-red-700 dark:text-red-300 font-medium">Worst EV</div>
                  <div className="font-mono text-red-600 dark:text-red-400">
                    {result.worst_ev_bb >= 0 ? '+' : ''}{result.worst_ev_bb.toFixed(2)}bb
                  </div>
                </div>
              </div>

              <div className="text-xs text-dark-500 dark:text-dark-400">
                EV Loss: <span className="font-mono text-red-600 dark:text-red-400">
                  {(result.best_ev_bb - result.user_ev_bb).toFixed(2)}bb
                </span>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}