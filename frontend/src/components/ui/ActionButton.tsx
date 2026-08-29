'use client';

import { Button } from './Button';
import { cn, evToColor, scoreToColor } from '@/lib/utils';
import type { QuizAction } from '@/types';

interface ActionButtonProps {
  action: QuizAction;
  isSelected?: boolean;
  isCorrect?: boolean;
  isGtoBest?: boolean;
  onClick: () => void;
  disabled?: boolean;
  showEV?: boolean;
  showGTO?: boolean;
  compact?: boolean;
}

export function ActionButton({
  action,
  isSelected = false,
  isCorrect,
  isGtoBest = false,
  onClick,
  disabled = false,
  showEV = true,
  showGTO = true,
  compact = false,
}: ActionButtonProps) {
  const isWrong = isSelected && !isCorrect && isCorrect !== undefined;
  const isRight = isSelected && isCorrect;

  return (
    <Button
      variant={isSelected ? (isRight ? 'primary' : 'danger') : isGtoBest ? 'outline' : 'secondary'}
      size={compact ? 'sm' : 'md'}
      className={cn(
        'w-full text-left gap-3',
        isSelected && 'ring-2 ring-offset-2',
        isRight && 'ring-green-500',
        isWrong && 'ring-red-500',
        isGtoBest && !isSelected && 'ring-1 ring-green-500'
      )}
      onClick={onClick}
      disabled={disabled}
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium truncate">{action.label}</span>
          {isGtoBest && (
            <span className="px-1.5 py-0.5 text-xs font-bold bg-green-100 text-green-700 rounded-full dark:bg-green-900/30 dark:text-green-300">
              GTO
            </span>
          )}
          {isRight && <span className="text-green-600 dark:text-green-400">✓</span>}
          {isWrong && <span className="text-red-600 dark:text-red-400">✗</span>}
        </div>
        <div className="flex items-center gap-3 mt-1 text-sm">
          {showGTO && (
            <span className={cn('font-mono', evToColor(action.gto_pct / 100))}>
              GTO: {action.gto_pct.toFixed(1)}%
            </span>
          )}
          {showEV && (
            <span className={cn('font-mono', evToColor(action.ev_bb))}>
              EV: {action.ev_bb >= 0 ? '+' : ''}{action.ev_bb.toFixed(2)}bb
            </span>
          )}
        </div>
      </div>
    </Button>
  );
}