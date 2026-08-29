import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatHand(hand: string): string {
  return hand.toUpperCase().replace(/SUITED|SUIT|s$/, 's').replace(/OFFSUIT|OFF|o$/, 'o');
}

export function parseHand(hand: string): { rank1: string; rank2: string; suited: boolean } {
  const clean = hand.toUpperCase().replace(/\s/g, '');
  if (clean.length === 2) {
    return { rank1: clean[0], rank2: clean[1], suited: clean[0] === clean[1] };
  }
  if (clean.length === 3) {
    return { rank1: clean[0], rank2: clean[1], suited: clean[2] === 'S' };
  }
  return { rank1: '', rank2: '', suited: false };
}

export function handToDisplay(hand: string): string {
  const { rank1, rank2, suited } = parseHand(hand);
  if (!rank1) return hand;
  if (rank1 === rank2) return `${rank1}${rank2}`;
  return `${rank1}${rank2}${suited ? 's' : 'o'}`;
}

export function evToColor(ev: number): string {
  if (ev > 0.5) return 'text-green-600 dark:text-green-400';
  if (ev > 0) return 'text-green-500 dark:text-green-300';
  if (ev > -0.5) return 'text-yellow-600 dark:text-yellow-400';
  if (ev > -1) return 'text-orange-600 dark:text-orange-400';
  return 'text-red-600 dark:text-red-400';
}

export function scoreToColor(score: number): string {
  if (score >= 90) return 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20';
  if (score >= 70) return 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20';
  if (score >= 50) return 'text-yellow-600 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-900/20';
  if (score >= 30) return 'text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-900/20';
  return 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20';
}

export function verdictToColor(verdict: string): string {
  switch (verdict) {
    case 'GTO':
      return 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20';
    case 'ok':
      return 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20';
    default:
      return 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20';
  }
}

export function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

export function formatNumber(num: number): string {
  if (num >= 1_000_000) return (num / 1_000_000).toFixed(1) + 'M';
  if (num >= 1_000) return (num / 1_000).toFixed(1) + 'K';
  return num.toString();
}

export const RANKS = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2'];

export function generateHandMatrix(): string[][] {
  const matrix: string[][] = [];
  for (let i = 0; i < 13; i++) {
    const row: string[] = [];
    for (let j = 0; j < 13; j++) {
      if (i === j) {
        row.push(`${RANKS[i]}${RANKS[j]}`);
      } else if (i < j) {
        row.push(`${RANKS[i]}${RANKS[j]}s`);
      } else {
        row.push(`${RANKS[j]}${RANKS[i]}o`);
      }
    }
    matrix.push(row);
  }
  return matrix;
}

export function getHandMatrixPosition(hand: string): { row: number; col: number } | null {
  const { rank1, rank2, suited } = parseHand(hand);
  if (!rank1) return null;
  const i = RANKS.indexOf(rank1);
  const j = RANKS.indexOf(rank2);
  if (i === -1 || j === -1) return null;
  if (i === j) return { row: i, col: i };
  if (suited) return { row: Math.min(i, j), col: Math.max(i, j) };
  return { row: Math.max(i, j), col: Math.min(i, j) };
}

export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export function debounce<T extends (...args: unknown[]) => unknown>(
  fn: T,
  ms: number
): (...args: Parameters<T>) => void {
  let timeoutId: ReturnType<typeof setTimeout>;
  return (...args: Parameters<T>) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn(...args), ms);
  };
}