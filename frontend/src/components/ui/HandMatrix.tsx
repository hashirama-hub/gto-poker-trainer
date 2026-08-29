'use client';

import { cn, generateHandMatrix, getHandMatrixPosition, handToDisplay, RANKS } from '@/lib/utils';

interface HandMatrixProps {
  highlights?: Record<string, { color: string; label?: string }>;
  onClick?: (hand: string) => void;
  className?: string;
  showLabels?: boolean;
  cellSize?: number;
}

export function HandMatrix({
  highlights = {},
  onClick,
  className,
  showLabels = true,
  cellSize = 36,
}: HandMatrixProps) {
  const matrix = generateHandMatrix();

  const getCellStyle = (hand: string) => {
    const highlight = highlights[hand];
    if (highlight) {
      return {
        backgroundColor: highlight.color,
        borderColor: highlight.color,
      };
    }
    return {};
  };

  const getTextColor = (hand: string) => {
    const highlight = highlights[hand];
    if (highlight) return '#ffffff';
    const pos = getHandMatrixPosition(hand);
    if (!pos) return '#1e293b';
    return pos.row === pos.col ? '#1e293b' : pos.row < pos.col ? '#059669' : '#dc2626';
  };

  return (
    <div className={cn('inline-block', className)}>
      {showLabels && (
        <div className="flex items-center justify-center gap-1 mb-1">
          <div className={`w-${cellSize}px`} />
          {RANKS.map((r) => (
            <div key={r} className="text-xs font-medium text-dark-500 dark:text-dark-400 w-[36px] text-center">
              {r}
            </div>
          ))}
        </div>
      )}
      <div className="grid grid-cols-13 gap-1">
        {matrix.map((row, rowIdx) => (
          <div key={rowIdx} className="flex items-center gap-1">
            {showLabels && (
              <div className="text-xs font-medium text-dark-500 dark:text-dark-400 w-[20px] text-right pr-1">
                {RANKS[rowIdx]}
              </div>
            )}
            {row.map((hand, colIdx) => {
              const displayHand = handToDisplay(hand);
              const pos = getHandMatrixPosition(hand);
              const isPair = pos?.row === pos?.col;
              const isSuited = pos !== null && pos.row < pos.col;
              const isOffsuit = pos !== null && pos.row > pos.col;
              const highlight = highlights[hand];

              return (
                <button
                  key={hand}
                  onClick={() => onClick?.(hand)}
                  disabled={!onClick}
                  className={cn(
                    'relative rounded-lg transition-all duration-150',
                    'focus:outline-none focus:ring-2 focus:ring-primary-500',
                    'disabled:opacity-40 disabled:cursor-not-allowed',
                    highlight && 'ring-2 ring-offset-2 ring-white',
                    `w-[${cellSize}px] h-[${cellSize}px]`
                  )}
                  style={{
                    ...getCellStyle(hand),
                    color: getTextColor(hand),
                    fontWeight: isPair ? 700 : 500,
                    fontSize: `${Math.max(10, cellSize * 0.28)}px`,
                  }}
                  title={hand}
                >
                  {displayHand}
                  {highlight?.label && (
                    <span
                      className="absolute bottom-0 right-0 text-[8px] bg-white/90 dark:bg-dark-900/90 rounded px-0.5"
                    >
                      {highlight.label}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        ))}
      </div>
      <div className="flex items-center gap-2 mt-2 text-xs text-dark-500 dark:text-dark-400">
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded bg-green-600" />
          Suited
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded bg-red-600" />
          Offsuit
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded bg-dark-800 dark:bg-dark-200" />
          Pairs
        </span>
      </div>
    </div>
  );
}

export function RangeDisplay({
  ranges,
  className,
}: {
  ranges: Record<string, { freq: number; action: string }>;
  className?: string;
}) {
  const highlights: Record<string, { color: string; label?: string }> = {};

  Object.entries(ranges).forEach(([hand, { freq, action }]) => {
    const intensity = Math.min(freq, 1);
    let color = '#64748b';
    if (action === 'raise' || action === 'shove') color = `rgb(${Math.round(220 * intensity)}, ${Math.round(38 * (1 - intensity))}, ${Math.round(38 * (1 - intensity))})`;
    else if (action === 'call') color = `rgb(${Math.round(34 * intensity)}, ${Math.round(197 * intensity)}, ${Math.round(94 * intensity)})`;
    else if (action === 'fold') color = `rgb(${Math.round(100 * (1 - intensity))}, ${Math.round(116 * (1 - intensity))}, ${Math.round(139 * (1 - intensity))})`;

    highlights[hand] = {
      color,
      label: `${Math.round(freq * 100)}%`,
    };
  });

  return <HandMatrix highlights={highlights} className={className} cellSize={32} />;
}