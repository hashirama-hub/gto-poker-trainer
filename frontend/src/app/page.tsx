'use client';

import Link from 'next/link';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { cn } from '@/lib/utils';
import { Play, Trophy, Brain, Zap, Shield, BarChart3, Settings, Github, ExternalLink } from 'lucide-react';

const FEATURES = [
  {
    icon: Zap,
    title: 'Instant Push/Fold',
    desc: 'Pre-solved 10/15/20bb chip-EV models. Sub-millisecond feedback. Perfect for shallow-stack MTT mastery.',
    color: 'from-yellow-500 to-orange-500',
  },
  {
    icon: Trophy,
    title: 'ICM Final Table',
    desc: 'Exact Malmuth-Harville ICM for 8-max. Real payout structures. On-demand solving (~1-2 min). Tournament-accurate.',
    color: 'from-purple-500 to-pink-500',
  },
  {
    icon: Brain,
    title: '100bb Full Tree',
    desc: 'Preflop + postflop solver (75k+ iters). SB vs BB 2.5x open. Board-averaged GTO strategies.',
    color: 'from-blue-500 to-cyan-500',
  },
  {
    icon: Shield,
    title: 'Flop Subgames',
    desc: 'Board-specific SRP flop solves. SB 2.5x, BB calls. On-demand (~2-5 min). Real postflop decisions.',
    color: 'from-green-500 to-teal-500',
  },
  {
    icon: BarChart3,
    title: 'EV-Based Scoring',
    desc: 'Score = (Your EV - Worst EV) / (Best EV - Worst EV). Partial credit for close decisions. 100 = exact GTO.',
    color: 'from-indigo-500 to-purple-500',
  },
  {
    icon: Settings,
    title: 'Deep Training Modes',
    desc: 'Quiz sessions with history, range matrices, EV analysis, action frequency breakdown. Track improvement over time.',
    color: 'from-red-500 to-rose-500',
  },
];

const STATS = [
  { label: 'Push/Fold Models', value: '3', desc: '10/15/20bb pre-solved' },
  { label: 'Full Tree Iters', value: '75k+', desc: '100bb SB vs BB' },
  { label: 'Test Coverage', value: '46', desc: 'Unit tests passing' },
  { label: 'Solver Speed', value: '~86 it/s', desc: 'Full tree MCCFR' },
];

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-dark-50 to-dark-100 dark:from-dark-950 dark:to-dark-900">
      <nav className="border-b border-dark-200 dark:border-dark-800 bg-white/80 dark:bg-dark-950/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <Link href="/" className="flex items-center gap-2 text-xl font-bold text-primary-600 dark:text-primary-400">
              <Zap className="w-7 h-7" />
              <span>GTO Trainer</span>
            </Link>
            <div className="flex items-center gap-6">
              <Link href="/quiz" className="text-dark-600 dark:text-dark-300 hover:text-primary-600 dark:hover:text-primary-400 font-medium">
                Train
              </Link>
              <Link href="/gto" className="text-dark-600 dark:text-dark-300 hover:text-primary-600 dark:hover:text-primary-400 font-medium">
                GTO Lookup
              </Link>
              <Link href="/models" className="text-dark-600 dark:text-dark-300 hover:text-primary-600 dark:hover:text-primary-400 font-medium">
                Models
              </Link>
              <a
                href="https://github.com/hashirama-hub/gto-poker-trainer"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-dark-500 dark:text-dark-400 hover:text-primary-600 dark:hover:text-primary-400"
              >
                <Github className="w-5 h-5" />
              </a>
              <Button size="sm" asChild>
                <Link href="/quiz"><Play className="w-4 h-4 mr-2" />Start Training</Link>
              </Button>
            </div>
          </div>
        </div>
      </nav>

      <main>
        <section className="relative py-20 lg:py-32 overflow-hidden">
          <div className="absolute inset-0 bg-gradient-radial from-primary-500/10 via-transparent to-transparent" />
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative">
            <div className="text-center max-w-3xl mx-auto mb-16">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 text-sm font-medium mb-6">
                <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                Live solver backend • Models auto-saved to GitHub
              </div>
              <h1 className="text-5xl lg:text-7xl font-bold text-dark-900 dark:text-dark-50 tracking-tight mb-6">
                Deep GTO Training{' '}
                <span className="bg-gradient-to-r from-primary-600 to-purple-600 bg-clip-text text-transparent">
                  for MTT Poker
                </span>
              </h1>
              <p className="text-xl text-dark-600 dark:text-dark-300 mb-8 max-w-2xl mx-auto">
                Built on a custom CFR solver with exact ICM. Train push/fold, preflop, and postflop spots
                with EV-based scoring that rewards precision, not just binary right/wrong.
              </p>
              <div className="flex items-center justify-center gap-4">
                <Button size="xl" asChild className="gap-2">
                  <Link href="/quiz"><Play className="w-5 h-5" />Start Training Now</Link>
                </Button>
                <Button variant="outline" size="xl" asChild className="gap-2">
                  <Link href="/gto"><Brain className="w-5 h-5" />Explore GTO Strategies</Link>
                </Button>
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-16">
              {STATS.map((stat) => (
                <Card key={stat.label} variant="outlined" className="text-center">
                  <CardContent className="py-6">
                    <div className="text-3xl lg:text-4xl font-bold text-primary-600 dark:text-primary-400">{stat.value}</div>
                    <div className="text-dark-600 dark:text-dark-300 font-medium">{stat.label}</div>
                    <div className="text-xs text-dark-500 dark:text-dark-400 mt-1">{stat.desc}</div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        </section>

        <section className="py-20 lg:py-28 bg-white dark:bg-dark-950">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-16">
              <h2 className="text-3xl lg:text-4xl font-bold text-dark-900 dark:text-dark-50 mb-4">Training Modes</h2>
              <p className="text-dark-600 dark:text-dark-400 max-w-2xl mx-auto">
                Each mode targets a specific MTT skill. Start with push/fold for ICM fundamentals,
                progress to full-tree preflop, then master board-specific flop play.
              </p>
            </div>

            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {FEATURES.map((feature, i) => (
                <Card key={feature.title} variant="elevated" className="group hover:shadow-xl transition-shadow duration-300 h-full">
                  <CardHeader>
                    <div className={cn('w-12 h-12 rounded-xl flex items-center justify-center', `bg-gradient-to-br ${feature.color}`)}>
                      <feature.icon className="w-6 h-6 text-white" />
                    </div>
                    <CardTitle className="mt-4">{feature.title}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-dark-600 dark:text-dark-300">{feature.desc}</p>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        </section>

        <section className="py-20 lg:py-28 bg-dark-50 dark:bg-dark-900">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid gap-12 lg:grid-cols-2 items-center">
              <div>
                <h2 className="text-3xl lg:text-4xl font-bold text-dark-900 dark:text-dark-50 mb-6">
                  How It Works
                </h2>
                <div className="space-y-6">
                  {[
                    'Choose a training mode: Push/Fold, ICM, Preflop, or Flop',
                    'Answer GTO questions — see action frequencies & EVs instantly',
                    'Get scored on EV difference from GTO (100 = perfect, 0 = worst)',
                    'Review mistakes with range matrices & action breakdowns',
                    'Track progress over sessions — identify leaks systematically',
                  ].map((step, i) => (
                    <div key={i} className="flex gap-4">
                      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary-600 text-white flex items-center justify-center font-bold text-lg">
                        {i + 1}
                      </div>
                      <div className="pt-1">
                        <p className="text-dark-700 dark:text-dark-200 font-medium">{step}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              <div className="relative">
                <Card variant="felt" className="aspect-square max-w-md mx-auto">
                  <div className="flex items-center justify-center h-full text-dark-100">
                    <div className="text-center">
                      <div className="text-6xl font-bold mb-2">A♠ K♠</div>
                      <div className="text-2xl font-mono text-green-400">EV: +2.34bb</div>
                      <div className="text-sm text-dark-300 mt-1">GTO: Raise 98%, Fold 2%</div>
                    </div>
                  </div>
                </Card>
              </div>
            </div>
          </div>
        </section>

        <section className="py-20 lg:py-28 bg-white dark:bg-dark-950">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <h2 className="text-3xl lg:text-4xl font-bold text-dark-900 dark:text-dark-50 mb-4">
              Built for Serious Players
            </h2>
            <p className="text-dark-600 dark:text-dark-400 max-w-2xl mx-auto mb-12">
              Not a toy. A training tool powered by a from-scratch MCCFR solver with exact ICM,
              blocker-corrected terminal values, and proper net payoff accounting.
            </p>
            <div className="flex items-center justify-center gap-8 text-sm text-dark-500 dark:text-dark-400">
              <div className="flex items-center gap-2"><Shield className="w-4 h-4" /><span>Net payoff (not gross)</span></div>
              <div className="flex items-center gap-2"><Brain className="w-4 h-4" /><span>Blocker-corrected EVs</span></div>
              <div className="flex items-center gap-2"><BarChart3 className="w-4 h-4" /><span>Jensen-bias-free exploitability</span></div>
              <div className="flex items-center gap-2"><Github className="w-4 h-4" /><span>Open source on GitHub</span></div>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-dark-200 dark:border-dark-800 bg-white dark:bg-dark-950 py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-dark-500 dark:text-dark-400">
              <Zap className="w-5 h-5" />
              <span>GTO Poker Trainer v0.2.0</span>
            </div>
            <div className="flex items-center gap-6 text-sm text-dark-500 dark:text-dark-400">
              <a href="https://github.com/hashirama-hub/gto-poker-trainer" target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 hover:text-primary-600">
                <Github className="w-4 h-4" />
                Source
              </a>
              <a href="https://github.com/hashirama-hub/gto-poker-trainer/issues" target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 hover:text-primary-600">
                <ExternalLink className="w-4 h-4" />
                Issues
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}