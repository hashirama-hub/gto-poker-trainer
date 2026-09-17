# P0 — Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the monorepo, validate the TexasSolver interface, and build the pure-TypeScript `core` domain library (cards, notation, ranges, spot config) plus the initial SQLite schema — the foundation every later phase depends on.

**Architecture:** npm-workspaces monorepo with a pure `@gto/core` package (no I/O, fully unit-testable) and a `@gto/db` package (Drizzle + better-sqlite3). A timeboxed spike documents TexasSolver's CLI and output format before P1 builds the adapter. `run.sh verify` gates typecheck + tests + build.

**Tech Stack:** Node 20, TypeScript (strict), npm workspaces, Vitest, Drizzle ORM, better-sqlite3.

**Spec:** `docs/superpowers/specs/2026-09-17-gto-mtt-trainer-design.md`

## Global Constraints

- Node.js >= 20, npm >= 10.
- TypeScript `strict: true` across all packages.
- Monorepo layout: `apps/*`, `packages/*`, `scripts/*` as npm workspaces.
- Card encoding: `card = rank * 4 + suit`; rank `2..A = 0..12`; suit `c,d,h,s = 0,1,2,3`.
- Hand class notation: pairs `AA` (6 combos), suited `AKs` (4), offsuit `AKo` (12); `+` expands upward (GTO Wizard notation).
- `NUM_COMBOS = 1326`; combo enumeration `for i in 0..51: for j in i+1..51`.
- Game format: 8-max MTT, big-blind ante `BBA = 1bb`.
- Only converged solutions (`exploitability <= 0.5%` pot) may be used by training; not relevant to P0 code but informs `solutions.status`.
- Code and identifiers in English.
- `run.sh verify` MUST run typecheck + tests + build and exit non-zero on failure.
- Engine version pin for later phases: `tree_version` string, initial value `"mtt8-bba-v1"`.

---

### Task 1: TexasSolver CLI/output spike

**Files:**
- Create: `docs/spikes/texassolver-cli.md`

**Interfaces:**
- Consumes: nothing.
- Produces: documented facts used by P1 — install path, exact solve command, config file schema, output file format, exploitability field location.

- [ ] **Step 1: Timebox the investigation (60–90 min)**

Attempt, in order, until one works:
1. Check for a prebuilt Linux release: `https://github.com/bupticybee/TexasSolver/releases`
2. Download and extract the release to `tools/texassolver/` (keep the binary out of git).
3. If no usable release, build from source per the repo README (CMake + a C++ compiler).

Record the exact commands run and their results.

- [ ] **Step 2: Run one tiny end-to-end solve**

Create a minimal config (a single-street or small-bet-size tree on a simple board, e.g. `AhKd2c`, small ranges, `accuracy`/`max_iteration` low) and run the solver headless. Capture stdout/stderr.

- [ ] **Step 3: Locate and capture the output format**

Identify where per-node strategy, per-hand frequencies, EV, and exploitability are written (JSON dump, CSV, or resource files). Copy a small representative snippet into the findings doc.

- [ ] **Step 4: Write the findings document**

Create `docs/spikes/texassolver-cli.md` with these headings, each filled with real observed values (no guesses):

```markdown
# TexasSolver CLI Spike Findings

## Install
- Path chosen:
- Version / commit:
- Exact build or download commands:

## Solve invocation
- Command:
- Config file format (paste a minimal example):
- Accuracy / exploitability knob:

## Output format
- Output location(s):
- Strategy representation (paste a snippet):
- Where per-hand EV lives:
- Where exploitability lives:

## Integration notes / uncertainties
- Dead ends:
- Open questions for the adapter:
```

- [ ] **Step 5: Commit**

```bash
git add docs/spikes/texassolver-cli.md
git commit -m "docs: add TexasSolver CLI spike findings"
```

---

### Task 2: Monorepo skeleton and verify command

**Files:**
- Create: `package.json`
- Create: `tsconfig.base.json`
- Create: `vitest.config.ts`
- Create: `.gitignore`
- Create: `run.sh`
- Create: `packages/core/package.json`
- Create: `packages/core/tsconfig.json`
- Create: `packages/core/src/index.ts`

**Interfaces:**
- Consumes: nothing.
- Produces: workspace commands `npm run typecheck`, `npm run test:run`, `npm run build`; package name `@gto/core` importable from other workspaces.

- [ ] **Step 1: Create the root `package.json`**

```json
{
  "name": "gto-trainer",
  "version": "0.0.0",
  "private": true,
  "type": "module",
  "workspaces": ["packages/*", "apps/*", "scripts"],
  "scripts": {
    "typecheck": "tsc -b --pretty false",
    "test": "vitest run",
    "test:run": "vitest run",
    "build": "npm run typecheck",
    "clean": "rm -rf dist node_modules/.cache packages/*/dist"
  },
  "devDependencies": {
    "typescript": "^5.5.0",
    "vitest": "^2.0.0"
  }
}
```

- [ ] **Step 2: Create `tsconfig.base.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "strict": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,
    "composite": true,
    "verbatimModuleSyntax": true,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "forceConsistentCasingInFileNames": true
  }
}
```

- [ ] **Step 3: Create the root `tsconfig.json` (solution build)**

```json
{
  "files": [],
  "references": [{ "path": "packages/core" }]
}
```

- [ ] **Step 4: Create `packages/core` scaffold**

`packages/core/package.json`:

```json
{
  "name": "@gto/core",
  "version": "0.0.0",
  "private": true,
  "type": "module",
  "main": "./dist/index.js",
  "types": "./dist/index.d.ts",
  "exports": { ".": { "types": "./dist/index.d.ts", "default": "./dist/index.js" } },
  "scripts": {
    "build": "tsc -b --pretty false"
  }
}
```

`packages/core/tsconfig.json`:

```json
{
  "extends": "../../tsconfig.base.json",
  "compilerOptions": { "outDir": "dist", "rootDir": "src" },
  "include": ["src"],
  "exclude": ["src/**/*.test.ts"]
}
```

`packages/core/src/index.ts`:

```ts
export {};
```

- [ ] **Step 5: Create `vitest.config.ts`**

```ts
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    include: ['packages/**/*.test.ts', 'apps/**/*.test.ts'],
    environment: 'node',
  },
});
```

- [ ] **Step 6: Create `.gitignore`**

```gitignore
node_modules/
dist/
*.tsbuildinfo
tools/texassolver/
data/*.sqlite
data/*.sqlite-*
.env
```

- [ ] **Step 7: Create `run.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

case "${1:-run}" in
  typecheck) npm run typecheck ;;
  test) npm run test:run ;;
  build) npm run build ;;
  verify)
    npm run typecheck
    npm run test:run
    npm run build
    echo "[OK] verify green"
    ;;
  *) echo "usage: ./run.sh {verify|typecheck|test|build}" ; exit 1 ;;
esac
```

- [ ] **Step 8: Install and verify**

Run:
```bash
chmod +x run.sh
npm install
./run.sh verify
```
Expected: exit 0, "[OK] verify green".

- [ ] **Step 9: Commit**

```bash
git add package.json package-lock.json tsconfig.base.json tsconfig.json vitest.config.ts .gitignore run.sh packages/core
git commit -m "chore: add npm workspaces monorepo skeleton with verify"
```

---

### Task 3: Core cards module

**Files:**
- Create: `packages/core/src/cards.ts`
- Create: `packages/core/src/cards.test.ts`
- Modify: `packages/core/src/index.ts`

**Interfaces:**
- Consumes: nothing.
- Produces: `type Card = number`; `RANK_CHARS`, `SUIT_CHARS`; `parseCard(s: string): Card`; `cardToString(c: Card): string`; `parseCards(s: string): Card[]`.

- [ ] **Step 1: Write the failing test**

`packages/core/src/cards.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { cardToString, parseCard, parseCards } from './cards';

describe('cards', () => {
  it('encodes 2c as 0 and As as 51', () => {
    expect(parseCard('2c')).toBe(0);
    expect(parseCard('As')).toBe(51);
  });

  it('is case-insensitive', () => {
    expect(parseCard('aH')).toBe(parseCard('Ah'));
  });

  it('round-trips every card', () => {
    for (let c = 0; c < 52; c++) expect(parseCard(cardToString(c))).toBe(c);
  });

  it('rejects malformed input', () => {
    expect(() => parseCard('1c')).toThrow();
    expect(() => parseCard('Ax')).toThrow();
    expect(() => parseCard('A')).toThrow();
  });

  it('parses a board string', () => {
    expect(parseCards('Ah Kd 2c')).toEqual([parseCard('Ah'), parseCard('Kd'), parseCard('2c')]);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run packages/core/src/cards.test.ts`
Expected: FAIL — cannot resolve `./cards`.

- [ ] **Step 3: Implement `packages/core/src/cards.ts`**

```ts
export type Card = number;

export const RANK_CHARS = '23456789TJQKA';
export const SUIT_CHARS = 'cdhs';

export function parseCard(s: string): Card {
  if (s.length !== 2) throw new Error(`invalid card: "${s}"`);
  const rank = RANK_CHARS.indexOf(s[0].toUpperCase());
  const suit = SUIT_CHARS.indexOf(s[1].toLowerCase());
  if (rank < 0 || suit < 0) throw new Error(`invalid card: "${s}"`);
  return rank * 4 + suit;
}

export function cardToString(c: Card): string {
  if (!Number.isInteger(c) || c < 0 || c > 51) throw new Error(`invalid card: ${c}`);
  return RANK_CHARS[c >> 2] + SUIT_CHARS[c & 3];
}

export function parseCards(s: string): Card[] {
  const trimmed = s.trim();
  if (trimmed === '') return [];
  return trimmed.split(/\s+/).map(parseCard);
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run packages/core/src/cards.test.ts`
Expected: PASS.

- [ ] **Step 5: Export and commit**

Modify `packages/core/src/index.ts` to:

```ts
export * from './cards';
```

```bash
git add packages/core/src/cards.ts packages/core/src/cards.test.ts packages/core/src/index.ts
git commit -m "feat(core): add card encoding and parsing"
```

---

### Task 4: Core hand-class notation

**Files:**
- Create: `packages/core/src/notation.ts`
- Create: `packages/core/src/notation.test.ts`
- Modify: `packages/core/src/index.ts`

**Interfaces:**
- Consumes: `Card`, `RANK_CHARS`, `SUIT_CHARS` from `./cards`.
- Produces: `isPairClass`, `isSuitedClass`; `expandHandClass(cls: string): [Card, Card][]`; `handClassesForToken(token: string): string[]`.

- [ ] **Step 1: Write the failing test**

`packages/core/src/notation.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { cardToString } from './cards';
import { expandHandClass, handClassesForToken } from './notation';

describe('expandHandClass', () => {
  it('expands a pair to 6 combos', () => {
    expect(expandHandClass('AA')).toHaveLength(6);
  });

  it('expands suited to 4 combos of the same suit', () => {
    const combos = expandHandClass('AKs');
    expect(combos).toHaveLength(4);
    for (const [a, b] of combos) expect(a % 4).toBe(b % 4);
  });

  it('expands offsuit to 12 combos of differing suits', () => {
    const combos = expandHandClass('AKo');
    expect(combos).toHaveLength(12);
    for (const [a, b] of combos) expect(a % 4).not.toBe(b % 4);
  });

  it('orders the high card first', () => {
    const [a, b] = expandHandClass('AKo')[0];
    expect(cardToString(a)[0]).toBe('A');
    expect(cardToString(b)[0]).toBe('K');
  });
});

describe('handClassesForToken', () => {
  it('expands a pair plus', () => {
    expect(handClassesForToken('99+')).toEqual(['99', 'TT', 'JJ', 'QQ', 'KK', 'AA']);
  });

  it('expands a suited plus up to the highest kicker', () => {
    expect(handClassesForToken('AQs+')).toEqual(['AQs', 'AKs']);
  });

  it('expands an offsuit plus up to the highest kicker', () => {
    expect(handClassesForToken('KTo+')).toEqual(['KTo', 'KJo', 'KQo']);
  });

  it('treats a single class as itself', () => {
    expect(handClassesForToken('T9s')).toEqual(['T9s']);
  });
});
```

Semantics: for non-pairs the high card is fixed and the kicker increases up to one rank below the high card (`ATs+` -> `ATs, AJs, AQs, AKs`; `KTs+` -> `KTs, KJs, KQs`). A token whose kicker is already adjacent to the high card expands to itself.

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run packages/core/src/notation.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `packages/core/src/notation.ts`**

```ts
import { RANK_CHARS, SUIT_CHARS, type Card } from './cards';

const RANK_INDEX = (ch: string): number => {
  const i = RANK_CHARS.indexOf(ch.toUpperCase());
  if (i < 0) throw new Error(`invalid rank: "${ch}"`);
  return i;
};

export function isPairClass(cls: string): boolean {
  return cls.length === 2 && cls[0].toUpperCase() === cls[1].toUpperCase();
}

export function isSuitedClass(cls: string): boolean {
  return cls.length === 3 && cls[2].toLowerCase() === 's';
}

function orderRanks(r1: number, r2: number): [number, number] {
  return r1 >= r2 ? [r1, r2] : [r2, r1];
}

function classToString(rHigh: number, rLow: number, suffix: '' | 's' | 'o'): string {
  return RANK_CHARS[rHigh] + RANK_CHARS[rLow] + suffix;
}

export function expandHandClass(cls: string): [Card, Card][] {
  const out: [Card, Card][] = [];
  const pair = isPairClass(cls);
  if (pair) {
    const r = RANK_INDEX(cls[0]);
    for (let s1 = 0; s1 < 4; s1++)
      for (let s2 = s1 + 1; s2 < 4; s2++) out.push([r * 4 + s1, r * 4 + s2]);
    return out;
  }
  if (cls.length !== 3 || !'so'.includes(cls[2].toLowerCase())) {
    throw new Error(`invalid hand class: "${cls}"`);
  }
  const suited = cls[2].toLowerCase() === 's';
  const [rHigh, rLow] = orderRanks(RANK_INDEX(cls[0]), RANK_INDEX(cls[1]));
  if (rHigh === rLow) throw new Error(`pair must use two identical ranks: "${cls}"`);
  for (let s1 = 0; s1 < 4; s1++)
    for (let s2 = 0; s2 < 4; s2++) {
      if (suited && s1 !== s2) continue;
      if (!suited && s1 === s2) continue;
      out.push([rHigh * 4 + s1, rLow * 4 + s2]);
    }
  return out;
}

export function handClassesForToken(token: string): string[] {
  const plus = token.endsWith('+');
  const base = plus ? token.slice(0, -1) : token;
  if (isPairClass(base)) {
    const r = RANK_INDEX(base[0]);
    const max = plus ? RANK_CHARS.length - 1 : r;
    const out: string[] = [];
    for (let i = r; i <= max; i++) out.push(RANK_CHARS[i] + RANK_CHARS[i]);
    return out;
  }
  if (base.length !== 3) throw new Error(`invalid token: "${token}"`);
  const suffix = base[2].toLowerCase() as 's' | 'o';
  const r1 = RANK_INDEX(base[0]);
  const r2 = RANK_INDEX(base[1]);
  const [rHigh, rLow] = orderRanks(r1, r2);
  const out: string[] = [];
  const maxLow = plus ? rHigh - 1 : rLow;
  for (let low = rLow; low <= maxLow; low++) out.push(classToString(rHigh, low, suffix));
  return out;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run packages/core/src/notation.test.ts`
Expected: PASS.

- [ ] **Step 5: Export and commit**

Modify `packages/core/src/index.ts` to:

```ts
export * from './cards';
export * from './notation';
```

```bash
git add packages/core/src/notation.ts packages/core/src/notation.test.ts packages/core/src/index.ts
git commit -m "feat(core): add hand-class notation and expansion"
```

---

### Task 5: Core Range type

**Files:**
- Create: `packages/core/src/range.ts`
- Create: `packages/core/src/range.test.ts`
- Modify: `packages/core/src/index.ts`

**Interfaces:**
- Consumes: `parseCard`, `type Card` from `./cards`; `expandHandClass`, `handClassesForToken` from `./notation`.
- Produces: `NUM_COMBOS`, `COMBO_INDEX`, `Range` class with `fromNotation`, `fromHandClasses`, `weight`, `setWeight`, `combos`, `percentOfAll`, `toJSON`, `fromJSON`.

- [ ] **Step 1: Write the failing test**

`packages/core/src/range.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { Range, NUM_COMBOS } from './range';

describe('Range', () => {
  it('has 1326 combos total', () => {
    expect(NUM_COMBOS).toBe(1326);
  });

  it('parses AA as 6 combos', () => {
    const r = Range.fromNotation('AA');
    expect(r.combos()).toBe(6);
  });

  it('parses a comma list with plus notation', () => {
    const r = Range.fromNotation('99+, AQs+');
    // 99..AA = 6 pairs * 6 = 36; AQs,AKs = 2 * 4 = 8
    expect(r.combos()).toBe(44);
  });

  it('computes percent of all combos', () => {
    expect(Range.fromNotation('AA').percentOfAll()).toBeCloseTo(6 / 1326, 6);
  });

  it('round-trips through JSON', () => {
    const r = Range.fromNotation('AKs, QQ');
    const again = Range.fromJSON(r.toJSON());
    expect(again.combos()).toBe(r.combos());
  });

  it('supports weights', () => {
    const r = Range.fromNotation('AA');
    const [c0] = r.nonZeroCombos();
    r.setWeight(c0, 0.5);
    expect(r.weight(c0)).toBeCloseTo(0.5, 6);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run packages/core/src/range.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `packages/core/src/range.ts`**

```ts
import type { Card } from './cards';
import { expandHandClass, handClassesForToken } from './notation';

export const NUM_COMBOS = 1326;

function buildCombos(): [Card, Card][] {
  const combos: [Card, Card][] = [];
  for (let i = 0; i < 52; i++) for (let j = i + 1; j < 52; j++) combos.push([i, j]);
  return combos;
}

export const COMBOS: readonly [Card, Card][] = buildCombos();

export function comboKey(a: Card, b: Card): string {
  return a < b ? `${a}-${b}` : `${b}-${a}`;
}

export const COMBO_INDEX: ReadonlyMap<string, number> = new Map(
  COMBOS.map(([a, b], idx) => [comboKey(a, b), idx]),
);

export interface RangeJSON {
  v: 1;
  weights: number[];
}

export class Range {
  private readonly weights: Float32Array;

  constructor(weights?: Float32Array) {
    this.weights = weights ?? new Float32Array(NUM_COMBOS);
  }

  static fromHandClasses(classes: string[], weight = 1): Range {
    const r = new Range();
    for (const cls of classes)
      for (const [a, b] of expandHandClass(cls)) {
        const idx = COMBO_INDEX.get(comboKey(a, b));
        if (idx !== undefined) r.weights[idx] = weight;
      }
    return r;
  }

  static fromNotation(text: string, weight = 1): Range {
    const classes: string[] = [];
    for (const raw of text.split(',')) {
      const token = raw.trim();
      if (token === '') continue;
      classes.push(...handClassesForToken(token));
    }
    return Range.fromHandClasses(classes, weight);
  }

  static fromJSON(json: RangeJSON): Range {
    return new Range(Float32Array.from(json.weights));
  }

  weight(comboIndex: number): number {
    return this.weights[comboIndex];
  }

  setWeight(comboIndex: number, w: number): void {
    this.weights[comboIndex] = w;
  }

  combos(): number {
    let n = 0;
    for (const w of this.weights) if (w > 0) n++;
    return n;
  }

  nonZeroCombos(): number[] {
    const out: number[] = [];
    this.weights.forEach((w, i) => {
      if (w > 0) out.push(i);
    });
    return out;
  }

  percentOfAll(): number {
    return this.combos() / NUM_COMBOS;
  }

  toJSON(): RangeJSON {
    return { v: 1, weights: Array.from(this.weights) };
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run packages/core/src/range.test.ts`
Expected: PASS.

- [ ] **Step 5: Export and commit**

Modify `packages/core/src/index.ts` to:

```ts
export * from './cards';
export * from './notation';
export * from './range';
```

```bash
git add packages/core/src/range.ts packages/core/src/range.test.ts packages/core/src/index.ts
git commit -m "feat(core): add weighted Range type"
```

---

### Task 6: Core positions, actions, and MTT constants

**Files:**
- Create: `packages/core/src/constants.ts`
- Create: `packages/core/src/constants.test.ts`
- Modify: `packages/core/src/index.ts`

**Interfaces:**
- Consumes: nothing.
- Produces: `const Position` object + `type Position`; `POSITIONS_8MAX: Position[]`; `StackTier = 10 | 15 | 20 | 30 | 40 | 60 | 100`; `STACK_TIERS: StackTier[]`; `BBA_BB = 1`; `type Action`; `TREE_VERSION = 'mtt8-bba-v1'`.

- [ ] **Step 1: Write the failing test**

`packages/core/src/constants.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { BBA_BB, POSITIONS_8MAX, STACK_TIERS, TREE_VERSION } from './constants';

describe('constants', () => {
  it('has 8 ordered 8-max positions ending with BB', () => {
    expect(POSITIONS_8MAX).toHaveLength(8);
    expect(POSITIONS_8MAX[0]).toBe('UTG');
    expect(POSITIONS_8MAX[7]).toBe('BB');
  });

  it('has the configured stack tiers', () => {
    expect(STACK_TIERS).toEqual([10, 15, 20, 30, 40, 60, 100]);
  });

  it('uses a 1bb big-blind ante', () => {
    expect(BBA_BB).toBe(1);
  });

  it('pins the initial tree version', () => {
    expect(TREE_VERSION).toBe('mtt8-bba-v1');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run packages/core/src/constants.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `packages/core/src/constants.ts`**

```ts
export const Position = {
  UTG: 'UTG',
  UTG1: 'UTG1',
  MP: 'MP',
  HJ: 'HJ',
  CO: 'CO',
  BTN: 'BTN',
  SB: 'SB',
  BB: 'BB',
} as const;
export type Position = (typeof Position)[keyof typeof Position];

export const POSITIONS_8MAX: Position[] = [
  Position.UTG,
  Position.UTG1,
  Position.MP,
  Position.HJ,
  Position.CO,
  Position.BTN,
  Position.SB,
  Position.BB,
];

export type StackTier = 10 | 15 | 20 | 30 | 40 | 60 | 100;
export const STACK_TIERS: StackTier[] = [10, 15, 20, 30, 40, 60, 100];

export const BBA_BB = 1;

export const TREE_VERSION = 'mtt8-bba-v1';

export type Action =
  | { type: 'fold' }
  | { type: 'check' }
  | { type: 'call' }
  | { type: 'bet'; amount: number }
  | { type: 'raise'; amount: number }
  | { type: 'allin' };
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run packages/core/src/constants.test.ts`
Expected: PASS.

- [ ] **Step 5: Export and commit**

Modify `packages/core/src/index.ts` to:

```ts
export * from './cards';
export * from './notation';
export * from './range';
export * from './constants';
```

```bash
git add packages/core/src/constants.ts packages/core/src/constants.test.ts packages/core/src/index.ts
git commit -m "feat(core): add positions, actions, and MTT constants"
```

---

### Task 7: Core SpotConfig canonicalization and hashing

**Files:**
- Create: `packages/core/src/spot.ts`
- Create: `packages/core/src/spot.test.ts`
- Modify: `packages/core/src/index.ts`

**Interfaces:**
- Consumes: `type Card`, `cardToString` from `./cards`; `type Position`, `POSITIONS_8MAX`, `type StackTier`, `type Action`, `TREE_VERSION`, `BBA_BB` from `./constants`.
- Produces: `interface SpotConfig`; `canonicalizeSpot(s: SpotConfig): string`; `hashSpot(s: SpotConfig): string`.

- [ ] **Step 1: Write the failing test**

`packages/core/src/spot.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { parseCards } from './cards';
import type { SpotConfig } from './spot';
import { canonicalizeSpot, hashSpot } from './spot';
import { TREE_VERSION } from './constants';

const base: SpotConfig = {
  format: 'MTT-8max',
  stackTier: 20,
  anteBb: 1,
  positions: ['BTN', 'BB'],
  stacksBb: [20, 20],
  board: parseCards('Ah Kd 2c'),
  preflopActions: [
    { actor: 'BTN', action: { type: 'raise', amount: 2.2 } },
    { actor: 'BB', action: { type: 'call' } },
  ],
  treeVersion: TREE_VERSION,
};

describe('SpotConfig', () => {
  it('canonicalizes deterministically regardless of key order', () => {
    const a = canonicalizeSpot(base);
    const b = canonicalizeSpot({ ...base });
    expect(a).toBe(b);
  });

  it('produces a stable hash', () => {
    expect(hashSpot(base)).toBe(hashSpot({ ...base }));
  });

  it('changes the hash when the board changes', () => {
    const other: SpotConfig = { ...base, board: parseCards('Ah Kd 2s') };
    expect(hashSpot(other)).not.toBe(hashSpot(base));
  });

  it('changes the hash when the tree version changes', () => {
    const other: SpotConfig = { ...base, treeVersion: 'mtt8-bba-v2' };
    expect(hashSpot(other)).not.toBe(hashSpot(base));
  });

  it('rejects duplicate board cards', () => {
    const bad: SpotConfig = { ...base, board: parseCards('Ah Ah 2c') };
    expect(() => canonicalizeSpot(bad)).toThrow();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run packages/core/src/spot.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `packages/core/src/spot.ts`**

```ts
import { createHash } from 'node:crypto';
import { cardToString, type Card } from './cards';
import { TREE_VERSION, type Action, type Position, type StackTier } from './constants';

export interface PreflopActionRecord {
  actor: Position;
  action: Action;
}

export interface SpotConfig {
  format: 'MTT-8max';
  stackTier: StackTier;
  anteBb: number;
  positions: Position[];
  stacksBb: number[];
  board: Card[];
  preflopActions: PreflopActionRecord[];
  treeVersion: string;
}

function actionKey(a: Action): string {
  switch (a.type) {
    case 'bet':
    case 'raise':
      return `${a.type}:${a.amount}`;
    default:
      return a.type;
  }
}

function assertValid(s: SpotConfig): void {
  if (s.board.length > 5) throw new Error('board cannot exceed 5 cards');
  const seen = new Set(s.board);
  if (seen.size !== s.board.length) throw new Error('duplicate board cards');
  if (s.positions.length !== s.stacksBb.length)
    throw new Error('positions and stacksBb must align');
}

export function canonicalizeSpot(s: SpotConfig): string {
  assertValid(s);
  return JSON.stringify({
    format: s.format,
    stackTier: s.stackTier,
    anteBb: s.anteBb,
    positions: s.positions,
    stacksBb: s.stacksBb,
    board: s.board.map(cardToString),
    preflopActions: s.preflopActions.map((r) => [r.actor, actionKey(r.action)]),
    treeVersion: s.treeVersion,
  });
}

export function hashSpot(s: SpotConfig): string {
  return createHash('sha256').update(canonicalizeSpot(s)).digest('hex');
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run packages/core/src/spot.test.ts`
Expected: PASS.

- [ ] **Step 5: Export and commit**

Modify `packages/core/src/index.ts` to:

```ts
export * from './cards';
export * from './notation';
export * from './range';
export * from './constants';
export * from './spot';
```

```bash
git add packages/core/src/spot.ts packages/core/src/spot.test.ts packages/core/src/index.ts
git commit -m "feat(core): add canonical SpotConfig and hashing"
```

---

### Task 8: DB package with initial schema

**Files:**
- Create: `packages/db/package.json`
- Create: `packages/db/tsconfig.json`
- Create: `packages/db/src/schema.ts`
- Create: `packages/db/src/client.ts`
- Create: `packages/db/src/client.test.ts`
- Create: `packages/db/src/migrations/0000_init.sql`
- Modify: `tsconfig.json`

**Interfaces:**
- Consumes: nothing at runtime.
- Produces: `createDb(path: string): DbHandle`; `runMigrations(handle, sql): void`; `type Db`; tables `spots`, `solutions`, `nodes`, `solveJobs`, `preflopCharts`.

- [ ] **Step 1: Add dependencies to `packages/db/package.json`**

```json
{
  "name": "@gto/db",
  "version": "0.0.0",
  "private": true,
  "type": "module",
  "main": "./dist/index.js",
  "types": "./dist/index.d.ts",
  "exports": { ".": { "types": "./dist/index.d.ts", "default": "./dist/index.js" } },
  "dependencies": {
    "better-sqlite3": "^11.0.0",
    "drizzle-orm": "^0.33.0"
  },
  "devDependencies": {
    "@types/better-sqlite3": "^7.6.0"
  },
  "scripts": { "build": "tsc -b --pretty false" }
}
```

- [ ] **Step 2: Create `packages/db/tsconfig.json`**

```json
{
  "extends": "../../tsconfig.base.json",
  "compilerOptions": { "outDir": "dist", "rootDir": "src" },
  "include": ["src"],
  "exclude": ["src/**/*.test.ts"]
}
```

- [ ] **Step 3: Create `packages/db/src/schema.ts`**

```ts
import { integer, real, sqliteTable, text, index } from 'drizzle-orm/sqlite-core';

export const spots = sqliteTable('spots', {
  id: text('id').primaryKey(),
  configHash: text('config_hash').notNull().unique(),
  format: text('format').notNull(),
  treeVersion: text('tree_version').notNull(),
  stackTier: integer('stack_tier').notNull(),
  config: text('config').notNull(),
  createdAt: integer('created_at').notNull(),
});

export const solutions = sqliteTable('solutions', {
  id: text('id').primaryKey(),
  spotId: text('spot_id').notNull().references(() => spots.id),
  status: text('status').notNull(),
  exploitability: real('exploitability'),
  elapsedMs: integer('elapsed_ms'),
  engineVersion: text('engine_version').notNull(),
  treeVersion: text('tree_version').notNull(),
  payload: text('payload'),
  createdAt: integer('created_at').notNull(),
});

export const nodes = sqliteTable(
  'nodes',
  {
    id: text('id').primaryKey(),
    solutionId: text('solution_id').notNull().references(() => solutions.id),
    path: text('path').notNull(),
    street: text('street').notNull(),
    board: text('board').notNull(),
  },
  (t) => ({ bySolutionPath: index('nodes_solution_path_idx').on(t.solutionId, t.path) }),
);

export const solveJobs = sqliteTable('solve_jobs', {
  id: text('id').primaryKey(),
  spotId: text('spot_id').notNull().references(() => spots.id),
  status: text('status').notNull(),
  priority: integer('priority').notNull(),
  attempts: integer('attempts').notNull().default(0),
  createdAt: integer('created_at').notNull(),
  updatedAt: integer('updated_at').notNull(),
});

export const preflopCharts = sqliteTable('preflop_charts', {
  id: text('id').primaryKey(),
  stackTier: integer('stack_tier').notNull(),
  position: text('position').notNull(),
  scenario: text('scenario').notNull(),
  action: text('action').notNull(),
  rangeData: text('range_data').notNull(),
  combos: integer('combos').notNull(),
  ev: real('ev'),
  source: text('source').notNull(),
});
```

- [ ] **Step 4: Create `packages/db/src/client.ts`**

```ts
import Database from 'better-sqlite3';
import { drizzle, type BetterSQLite3Database } from 'drizzle-orm/better-sqlite3';
import * as schema from './schema';

export type Db = BetterSQLite3Database<typeof schema>;

export interface DbHandle {
  db: Db;
  sqlite: Database.Database;
}

export function createDb(path: string): DbHandle {
  const sqlite = new Database(path);
  sqlite.pragma('journal_mode = WAL');
  sqlite.pragma('foreign_keys = ON');
  const db = drizzle(sqlite, { schema });
  return { db, sqlite };
}

export function runMigrations(handle: DbHandle, sql: string): void {
  handle.sqlite.exec(sql);
}
```

- [ ] **Step 5: Create `packages/db/src/migrations/0000_init.sql`**

```sql
CREATE TABLE IF NOT EXISTS spots (
  id TEXT PRIMARY KEY,
  config_hash TEXT NOT NULL UNIQUE,
  format TEXT NOT NULL,
  tree_version TEXT NOT NULL,
  stack_tier INTEGER NOT NULL,
  config TEXT NOT NULL,
  created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS solutions (
  id TEXT PRIMARY KEY,
  spot_id TEXT NOT NULL REFERENCES spots(id),
  status TEXT NOT NULL,
  exploitability REAL,
  elapsed_ms INTEGER,
  engine_version TEXT NOT NULL,
  tree_version TEXT NOT NULL,
  payload TEXT,
  created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS nodes (
  id TEXT PRIMARY KEY,
  solution_id TEXT NOT NULL REFERENCES solutions(id),
  path TEXT NOT NULL,
  street TEXT NOT NULL,
  board TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS nodes_solution_path_idx ON nodes(solution_id, path);

CREATE TABLE IF NOT EXISTS solve_jobs (
  id TEXT PRIMARY KEY,
  spot_id TEXT NOT NULL REFERENCES spots(id),
  status TEXT NOT NULL,
  priority INTEGER NOT NULL,
  attempts INTEGER NOT NULL DEFAULT 0,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS preflop_charts (
  id TEXT PRIMARY KEY,
  stack_tier INTEGER NOT NULL,
  position TEXT NOT NULL,
  scenario TEXT NOT NULL,
  action TEXT NOT NULL,
  range_data TEXT NOT NULL,
  combos INTEGER NOT NULL,
  ev REAL,
  source TEXT NOT NULL
);
```

- [ ] **Step 6: Write the failing test**

`packages/db/src/client.test.ts`:

```ts
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { createDb, runMigrations } from './client';
import { spots } from './schema';

const migration = readFileSync(
  fileURLToPath(new URL('./migrations/0000_init.sql', import.meta.url)),
  'utf8',
);

function memDb() {
  const handle = createDb(':memory:');
  runMigrations(handle, migration);
  return handle;
}

describe('db client', () => {
  it('creates all tables', () => {
    const { sqlite } = memDb();
    const rows = sqlite
      .prepare("SELECT name FROM sqlite_master WHERE type='table'")
      .all() as { name: string }[];
    const names = rows.map((r) => r.name);
    for (const t of ['spots', 'solutions', 'nodes', 'solve_jobs', 'preflop_charts'])
      expect(names).toContain(t);
  });

  it('enforces the unique config hash', () => {
    const { db } = memDb();
    const now = Date.now();
    const row = {
      id: 's1',
      configHash: 'abc',
      format: 'MTT-8max',
      treeVersion: 'mtt8-bba-v1',
      stackTier: 20,
      config: '{}',
      createdAt: now,
    };
    db.insert(spots).values(row).run();
    expect(() => db.insert(spots).values({ ...row, id: 's2' }).run()).toThrow();
  });
});
```

- [ ] **Step 7: Install deps and run the test to verify it passes**

Run: `npm install && npx vitest run packages/db/src/client.test.ts`
Expected: PASS. If the unique-constraint test fails, verify `config_hash` is declared `UNIQUE` in the migration.

- [ ] **Step 8: Verify and commit**

Modify root `tsconfig.json` references to include `packages/db`:

```json
{
  "files": [],
  "references": [{ "path": "packages/core" }, { "path": "packages/db" }]
}
```

```bash
./run.sh verify
git add packages/db tsconfig.json package-lock.json
git commit -m "feat(db): add SQLite schema and client for spots/solutions/jobs"
```

---

### Task 9: Export DB entrypoint and final verification

**Files:**
- Create: `packages/db/src/index.ts`
- Modify: `packages/db/package.json` (ensure `main` points at `dist/index.js`)

**Interfaces:**
- Consumes: `./client`, `./schema`.
- Produces: `@gto/db` re-exports `createDb`, `runMigrations`, `type Db`, and all schema tables.

- [ ] **Step 1: Create `packages/db/src/index.ts`**

```ts
export * from './client';
export * from './schema';
```

- [ ] **Step 2: Run the full verification**

Run: `./run.sh verify`
Expected: typecheck passes, all tests pass, build passes, "[OK] verify green".

- [ ] **Step 3: Commit and push**

```bash
git add packages/db/src/index.ts
git commit -m "feat(db): export package entrypoint"
git push origin main
```

---

## Self-Review

**Spec coverage (P0 scope only):**
- Spec §6 repository structure → Task 2 (workspaces, packages/core, packages/db). `apps/*`, `scripts/*`, `tools/` are created in later-phase plans.
- Spec §7 domain model (card encoding, positions, stack tiers, BBA, Action, SpotConfig, hash) → Tasks 3–7.
- Spec §9 data model (`spots`, `solutions`, `nodes`, `solve_jobs`, `preflop_charts`) → Task 8. Remaining tables (`ranges`, `hands`, `sessions`, `attempts`, `curriculum_modules`, `module_progress`, `leak_profile`, `coverage`) are added in the phases that use them (YAGNI).
- Spec §10 solver integration → Task 1 spike (validation only); adapter is P1.
- Spec §8 accuracy (`tree_version` pinning) → Task 6 `TREE_VERSION`, Task 7 hash includes it.
- Spec §15 testing → Vitest unit tests in every code task; `run.sh verify` in Tasks 2 and 9.
- Spec §16 P0 → this plan.

**Deferred to later plans (intentional):** solver adapter, orchestrator, farm, preflop precompute (P1); frontend/apps (P2+); equity/hand evaluator (simulator phase).

**Placeholder scan:** no "TBD/TODO"; the only investigative task (Task 1) has a concrete output and template.

**Type consistency:** `Card`, `Position`, `StackTier`, `Action`, `SpotConfig`, `Range`, `hashSpot`, `createDb`, `runMigrations`, and table names are used consistently across tasks.

**Known risks for the executor:**
- TexasSolver may be unavailable offline or fail to build; Task 1 must be timeboxed and its findings may force a P1 re-plan.
- `better-sqlite3` needs a native build toolchain; if install fails, record the error and escalate rather than switching databases.
- Disk has ~24 GB free; keep `tools/texassolver/` and solver outputs out of git.
