'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import { cn } from '@/lib/utils';
import { Play, Settings, HelpCircle } from 'lucide-react';

const MODES = [
  {
    id: 'pushfold',
    name: 'Push/Fold (Chip EV)',
    desc: 'SB shove or fold / BB call or fold. Pre-solved models, instant feedback.',
    icon: '⚡',
    color: 'from-yellow-500 to-orange-500',
    config: [
      { key: 'bb', label: 'Effective BB (0=random)', type: 'number', min: 8, max: 25, step: 1, default: 0 },
      { key: 'position', label: 'Position', type: 'select', options: ['sb', 'bb'], default: 'sb' },
    ],
  },
  {
    id: 'icm',
    name: 'ICM Push/Fold (8-max MTT)',
    desc: 'Full final table ICM. Solves on-demand (~1-2 min). Real tournament spots.',
    icon: '🏆',
    color: 'from-purple-500 to-pink-500',
    config: [
      { key: 'iterations', label: 'Iterations', type: 'number', min: 10000, max: 100000, step: 5000, default: 60000 },
      { key: 'position', label: 'Position', type: 'select', options: ['sb', 'bb'], default: 'sb' },
    ],
  },
  {
    id: 'preflop',
    name: '100bb Preflop (SB vs BB)',
    desc: 'Full preflop+postflop tree. Board-averaged strategy. Pre-solved 75k+ iterations.',
    icon: '🃏',
    color: 'from-blue-500 to-cyan-500',
    config: [
      { key: 'position', label: 'Position', type: 'select', options: ['sb', 'bb'], default: 'sb' },
    ],
  },
  {
    id: 'flop',
    name: 'Flop Subgame (SRP 2.5x)',
    desc: 'Board-specific flop solve. SB raised 2.5x, BB called. Solves on-demand (~2-5 min).',
    icon: '🌊',
    color: 'from-green-500 to-teal-500',
    config: [
      { key: 'fast', label: 'Fast mode (6k iters)', type: 'boolean', default: false },
      { key: 'board', label: 'Board cards (0-51, comma-separated)', type: 'text', default: '' },
    ],
  },
];

export function QuizSetup({ onStart }: { onStart: (mode: string, hands: number, config: Record<string, unknown>) => void }) {
  const [selectedMode, setSelectedMode] = useState('pushfold');
  const [hands, setHands] = useState(10);
  const [config, setConfig] = useState<Record<string, unknown>>({});
  const [loading, setLoading] = useState(false);

  const mode = MODES.find((m) => m.id === selectedMode)!;

  const handleConfigChange = (key: string, value: unknown) => {
    setConfig((prev) => ({ ...prev, [key]: value }));
  };

  const handleSubmit = async () => {
    setLoading(true);
    try {
      await onStart(selectedMode, hands, config);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="text-center">
        <h1 className="text-3xl font-bold text-dark-900 dark:text-dark-100 mb-2">GTO Trainer</h1>
        <p className="text-dark-500 dark:text-dark-400">Deep training for MTT poker. Choose a mode to begin.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {MODES.map((m) => (
          <Button
            key={m.id}
            variant={selectedMode === m.id ? 'primary' : 'outline'}
            size="lg"
            className={cn(
              'h-40 flex-col items-start text-left gap-3 p-5',
              selectedMode === m.id && 'ring-2 ring-primary-500 bg-primary-50 dark:bg-primary-900/20'
            )}
            onClick={() => {
              setSelectedMode(m.id);
              setConfig(
                Object.fromEntries(m.config.map((c) => [c.key, c.default]))
              );
            }}
          >
            <div className="flex items-center gap-3">
              <span className="text-4xl">{m.icon}</span>
              <div>
                <div className="font-semibold text-lg">{m.name}</div>
                <div className="text-sm text-dark-500 dark:text-dark-400 mt-1">{m.desc}</div>
              </div>
            </div>
          </Button>
        ))}
      </div>

      <Card variant="outlined">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="w-5 h-5" />
            {mode.name} Settings
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-sm font-medium text-dark-700 dark:text-dark-300">
              Hands:
              <input
                type="number"
                min="1"
                max="100"
                value={hands}
                onChange={(e) => setHands(Number(e.target.value))}
                className="w-20 px-2 py-1 border border-dark-300 dark:border-dark-600 rounded bg-white dark:bg-dark-800 text-dark-900 dark:text-dark-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </label>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            {mode.config.map((c) => (
              <div key={c.key} className="space-y-1">
                <label className="text-sm font-medium text-dark-700 dark:text-dark-300">
                  {c.label}
                </label>
                {c.type === 'number' && (
                  <input
                    type="number"
                    min={c.min}
                    max={c.max}
                    step={c.step}
                    value={config[c.key] as number}
                    onChange={(e) => handleConfigChange(c.key, Number(e.target.value))}
                    className="w-full px-3 py-2 border border-dark-300 dark:border-dark-600 rounded-lg bg-white dark:bg-dark-800 text-dark-900 dark:text-dark-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                )}
                {c.type === 'select' && (
                  <select
                    value={config[c.key] as string}
                    onChange={(e) => handleConfigChange(c.key, e.target.value)}
                    className="w-full px-3 py-2 border border-dark-300 dark:border-dark-600 rounded-lg bg-white dark:bg-dark-800 text-dark-900 dark:text-dark-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  >
                    {c.options.map((opt) => (
                      <option key={opt} value={opt}>
                        {opt.toUpperCase()}
                      </option>
                    ))}
                  </select>
                )}
                {c.type === 'boolean' && (
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={config[c.key] as boolean}
                      onChange={(e) => handleConfigChange(c.key, e.target.checked)}
                      className="w-4 h-4 text-primary-600 border-dark-300 rounded focus:ring-primary-500"
                    />
                    <span className="text-sm text-dark-700 dark:text-dark-300">Enable</span>
                  </label>
                )}
                {c.type === 'text' && (
                  <input
                    type="text"
                    value={config[c.key] as string}
                    onChange={(e) => handleConfigChange(c.key, e.target.value)}
                    placeholder={c.default as string}
                    className="w-full px-3 py-2 border border-dark-300 dark:border-dark-600 rounded-lg bg-white dark:bg-dark-800 text-dark-900 dark:text-dark-100 focus:outline-none focus:ring-2 focus:ring-primary-500 font-mono text-sm"
                  />
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Button
        size="xl"
        className="w-full py-4 text-lg"
        onClick={handleSubmit}
        disabled={loading}
        loading={loading}
      >
        <Play className="w-5 h-5 mr-2" />
        Start Training ({hands} hands)
      </Button>

      <div className="text-center text-sm text-dark-500 dark:text-dark-400">
        <HelpCircle className="w-4 h-4 inline mr-1" />
        Scoring: 100 = exact GTO EV, 0 = worst action. Partial credit for close decisions.
      </div>
    </div>
  );
}