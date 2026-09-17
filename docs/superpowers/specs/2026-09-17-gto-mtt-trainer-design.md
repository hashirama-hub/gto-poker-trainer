# GTO MTT Trainer — Design Specification

Date: 2026-09-17
Status: Approved (design)

## 1. Overview

A personal, single-user **web application** for training in-hand GTO play for
**8-max MTT** (No-Limit Hold'em, big-blind ante). The app simulates hands,
lets the user make decisions against GTO bots, grades each decision against a
self-hosted solver, and adapts a structured curriculum to the user's leaks.

It supersedes the earlier desktop cash-game `SPEC.md`; that document is kept
only as historical reference. This is a new web project.

### 1.1 Goal

Build a GTO-accurate training platform whose coverage grows over time via a
24/7 background solve farm, driven by an adaptive coaching engine.

### 1.2 Non-goals (v1)

- Replicating GTO Wizard's exact numbers or proprietary game trees.
- Multi-user accounts, cloud hosting, or remote access.
- Real-time multiway postflop GTO (not well-defined; see 3.2).
- ICM / tournament equity solving (deferred; extension point reserved).
- Exploitative / population-based opponents (deferred; GTO bots only in v1).

### 1.3 Definition of "GTO-accurate"

Solutions are considered valid when solved to a **low exploitability target**
(configurable, default <= 0.5% of pot) using a single, versioned, canonical
game-tree configuration. Only solutions meeting the target are served to
training. "Accurate" means strategically sound and internally consistent, not
numerically identical to any commercial product.

## 2. Key Decisions

| Area | Decision |
|---|---|
| Project | New web app, supersedes desktop `SPEC.md` |
| Deployment | Single-user, runs locally (backend + solver on user's machine, kept on 24/7) |
| Frontend | React 18 + TypeScript + Vite + Tailwind + shadcn/ui |
| Backend | Node 20 + Fastify + TypeScript |
| Database | SQLite (better-sqlite3 + Drizzle ORM) |
| Solver | TexasSolver, self-hosted, invoked via CLI; `SolverEngine` adapter interface |
| Game format | 8-max MTT, big-blind ante (BBA = 1bb) |
| Equity model | chip-EV first; ICM extension point reserved |
| GTO data | Preflop precomputed + postflop solve-on-demand with persistent cache |
| Background | 24/7 solve farm with coverage planner and night mode |
| Training | Structured curriculum with mastery gating + daily plan + spaced repetition |
| Opponents | GTO bots (sample from solver strategies) |
| Accuracy gate | Only solutions with exploitability <= threshold are trainable |

## 3. Constraints and Technical Realities

### 3.1 GTO depends on the game tree

GTO output is not unique. Frequencies and EVs change with bet-size abstraction,
raise sizes, all-in thresholds, rake, ante, and (for MTT) ICM. This app defines
and versions **one canonical tree** and is consistent with respect to it. Cross-
product numeric parity is explicitly out of scope.

### 3.2 Multiway postflop is not solved

Postflop GTO for 3+ players is not well-defined at practical scale (this holds
for commercial products too). Therefore:

- Grading is only performed where an exact reference solution exists for the
  actual line: **preflop scenarios** and **postflop when the pot is heads-up**.
- Lines that reach multiway postflop are marked **`no_reference`**: playable for
  experience, not graded, and not counted toward accuracy/mastery.

### 3.3 Solve cost

A quality MTT postflop solve with a fine tree is seconds-to-hours of CPU time.
The farm amortizes this over 24/7 operation; interactive requests prioritize
over background solving.

## 4. Architecture

```
Frontend (React/Vite/TS)
  - REST + SSE clients, Zustand (UI state), TanStack Query (server state)
  - Poker table (SVG/Canvas), range grid (virtualized DOM)
        |
        | REST + SSE
        v
Backend (Node/Fastify/TS)
  - REST API: spots, solutions, ranges, hands, sessions, curriculum, stats
  - SSE: solve progress, farm status
  - Training engine: drills, simulator, scoring, spaced repetition
  - Solver orchestrator: canonicalize -> hash -> cache -> queue -> parse
  - Solve farm: scheduler, coverage planner, night mode
  - HH parser
  - Coaching engine: leak profile, adaptive curriculum, daily plan
        |
        v
Storage (SQLite + Drizzle)
        |
        v
TexasSolver CLI (subprocess) [self-hosted, 24/7]
```

Boundaries:

- **`SolverEngine` interface** isolates engine specifics (`solve`, `getNodeStrategy`),
  so an ICM engine or PioSolver can be added without touching consumers.
- **Solve queue** is persisted in the database so restarts resume work.
- **Solution payloads** are stored as one compressed JSON document per solve;
  a light node index enables lookups. Solutions are read into memory and queried
  by node path.

## 5. Tech Stack

- Frontend: React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui (Radix), Zustand,
  TanStack Query, Vitest, Playwright.
- Backend: Node 20, Fastify, TypeScript, SSE, `p-queue` for worker concurrency,
  Drizzle ORM, better-sqlite3, Vitest.
- Shared: `packages/core` (pure TypeScript domain), `packages/solver`,
  `packages/db`.
- Monorepo: npm workspaces, single `tsconfig` base.
- Runner: root `run.sh` with `verify = typecheck + test + build`.

## 6. Repository Structure

```
gto-trainer/
├── apps/
│   ├── web/                 # React + Vite frontend
│   └── server/              # Fastify backend + API + SSE
├── packages/
│   ├── core/                # cards, ranges, game state, spot config, EV, scoring
│   ├── solver/              # SolverEngine interface, TexasSolver adapter, parser
│   └── db/                  # Drizzle schema + migrations (SQLite)
├── scripts/
│   ├── preflop-precompute.ts
│   └── warm-cache.ts
├── tools/texassolver/       # engine binary/path config (gitignored binary)
├── docs/superpowers/specs/  # design docs
├── run.sh
└── package.json
```

## 7. Domain Model

- **Card**: 0-51 = rank*4 + suit; rank 2..A = 0..12; suit c,d,h,s = 0..3.
- **HoleCards**: sorted unique pair.
- **BoardCards**: 3 (flop) + 1 (turn) + 1 (river).
- **Range**: weighted `Map<Hand, weight>` over 1326 combos; serializable/compressed.
- **Positions (8-max)**: UTG, UTG1, MP, HJ, CO, BTN, SB, BB (8 seats).
- **Stack tiers**: 10, 15, 20, 30, 40, 60, 100 bb (configurable set).
- **Ante**: BBA = 1bb, posted by BB; pot computed accordingly.
- **Action**: Fold | Check | Call | Bet(amount) | Raise(amount) | AllIn.
- **SpotConfig** (canonical): positions, stacks, ante, board, preflop action
  sequence, tree config version, stack tier. Serialized canonically and hashed.
- **NodePath**: street + board + action sequence identifying a decision node.
- **NodeStrategy**: for a node, per-hand action frequencies + EVs (bb).
- **Reference**: whether a node has a valid, converged solution.

## 8. Accuracy Strategy

### 8.1 Canonical tree (versioned)

- Preflop: open sizes by depth (2.2-2.5bb deep; limp/raise short), 3bet IP/OOP,
  4bet, jam thresholds by stack tier.
- Postflop: bet sizes {33%, 75%, 125%} + all-in; raise {50%, 100%} pot; bounded
  all-in threshold.
- Rake: postflop rake = 0 (MTT fees are at entry).
- Ante: BBA = 1bb; pot math includes ante.
- The tree config is a single versioned artifact referenced by every solve and
  stored on each solution record (`tree_version`).

### 8.2 Convergence gate

- `exploitability_target` configurable; default <= 0.5% pot.
- Each solution stores measured `exploitability` and `elapsed_ms`.
- Only `status = ready AND exploitability <= target` solutions are used by
  training, explorer, simulator, HH review, and the coaching engine.

### 8.3 Validation harness

- Per-node invariant: action frequencies sum to 1 (within tolerance).
- EV consistency checks across the tree.
- Golden spots with known expected frequencies within tolerance.

## 9. Data Model (SQLite)

| Table | Purpose |
|---|---|
| `spots` | canonical spot config + `config_hash`, tree version, metadata |
| `solutions` | one row per solve: `spot_id`, `status`, `exploitability`, `elapsed_ms`, `engine_version`, `tree_version`, compressed `payload` |
| `nodes` | lightweight index: `solution_id`, `path`, `street`, `board` |
| `preflop_charts` | precomputed per depth x position x scenario x action: range, combos, EV |
| `ranges` | user-authored/imported ranges |
| `hands` | parsed HH + per-street review results |
| `drill_spots` | curated training spot library |
| `sessions` | training session: mode, score, duration |
| `attempts` | each answer: correct, ev_loss, `due_at` (SM-2), `leak_tag` |
| `solve_jobs` | persistent queue: `status`, `priority`, `spot_id`, `attempts`, timestamps |
| `curriculum_modules` | slug, title, order, prerequisites, `spot_filter`, `mastery_criteria`, `status` |
| `module_progress` | module_id, attempts, accuracy, avg_ev_loss, `mastered_at` |
| `leak_profile` | aggregated per-dimension error stats for coaching |
| `coverage` | coverage targets and completion stats for the farm |

## 10. Solver Integration

`SolverEngine` interface:

```
solve(spotConfig): Promise<Solution>
getNodeStrategy(solution, nodePath): NodeStrategy
```

Flow:

1. Canonicalize `SpotConfig` -> canonical form -> `config_hash`.
2. Cache lookup in `solutions`.
3. On miss: create `solve_jobs` entry, enqueue; expose progress via SSE.
4. Run TexasSolver CLI with a generated config file; parse output
   (strategy/frequencies/EV, exploitability); normalize to engine-agnostic
   `NodeStrategy`.
5. Persist solution payload + node index.
6. Mark `ready` only when converged; otherwise `failed`/`rejected`.

The exact TexasSolver CLI/output format is **validated first** in Phase 0 via a
small end-to-end spike before dependent work begins.

## 11. Solve Farm (24/7)

- **Scheduler + worker pool**: continuous, configurable concurrency/threads.
  Interactive jobs jump the queue; farm yields CPU during interactive solves.
- **Coverage planner**: enumerates the target spot space (depth x position x
  scenario x board class), orders by practical frequency (common depths and
  board classes first), dedupes via `config_hash`, tracks `coverage`.
- **Night mode**: configurable window (e.g. 00:00-08:00) for full-throughput
  solving; daytime reduces load or runs only when idle.
- **Resume**: jobs persist; backend restart resumes.
- **Dashboard**: coverage %, solves/hour, ETA, exploitability distribution,
  recent jobs.

## 12. Preflop Precompute

- Offline script solves/loads preflop charts across the depth x position x
  scenario matrix and writes `preflop_charts`.
- Preflop space is small; charts are served instantly and power the preflop
  trainer, simulator preflop decisions, and HH review.

## 13. Feature Modules

### 13.1 Range builder

- 13x13 grid (pairs, suited, offsuit); click toggle, weight slider, drag multi-select.
- Groups by position and by scenario; import/export text notation ("AKs, AQs+, 99+"),
  JSON, and PioSolver format.
- Stats: combo count, % of hands, EV vs range.
- Ranges feed the explorer and simulator.

### 13.2 Preflop chart trainer

- Charts per depth x position x scenario; quiz presents a random hand and asks
  for the action; heatmap view.
- Scored via freq-weighted accuracy; immediate feedback.
- Fully served from `preflop_charts` (instant).

### 13.3 Postflop spot explorer

- Build a spot (board, positions, stacks, action line); view tree, node
  frequencies and EVs, runout aggregation.
- Reads cache; missing spots enqueue a solve with SSE progress.
- Only converged solutions are shown.

### 13.4 In-hand trainer + simulator

- **In-hand trainer**: presents a single spot; hero chooses an action; feedback
  shows GTO frequencies, alternatives, and EV loss (bb).
- **Simulator**: deals full 8-max hands at a chosen stack depth; opponents are
  GTO bots that sample from solver strategies. Hero plays decision by decision.
  Each hero decision with a reference is graded (freq-weighted score + EV loss).
  Lines reaching multiway postflop are `no_reference` (not graded).
  Missing references trigger background solves.
- Shared table UI; post-hand review replays decisions.

### 13.5 Coaching engine + curriculum + daily plan

- **Leak profile**: every decision recorded across dimensions (position, street,
  stack tier, hand class, pot type, action, EV loss); leaks ranked by
  `frequency x EV loss`.
- **Curriculum**: ordered modules by topic (e.g. Push/Fold 10-15bb -> RFI
  20-40bb -> BB Defense vs RFI -> 3bet Pots - Flop -> Turn/River barreling ->
  River bluffs & calls). Each module has a spot filter, drill pool, short
  explanation, prerequisites, and mastery criteria.
- **Mastery** example: accuracy >= 90% over the last >= 50 attempts AND average
  EV loss <= 0.15bb. Only then does the next module unlock.
- Modules needing unfarmed spots show a "precomputing" state with farm progress.
- **Daily plan**: generated with a seeded RNG (same seed reproduces the plan)
  from the current unlocked module plus due spaced-repetition items; default
  goal 25 decisions, with an unlimited free-play mode.
- **Spaced repetition**: SM-2 scheduling on missed spots via `attempts.due_at`.
- **Explanations**: generated from solver data using templates over frequencies,
  EVs, blockers, and equity.

### 13.6 Progress and leak detection

- Accuracy by spot type, street, action; EV-loss trends over time.
- Weak-spot ranking; streak and calendar heatmap; session history.

### 13.7 Hand history review

- Parser for PokerStars/GG 8-max MTT with BBA (manual entry and text paste).
- Maps each decision to a `SpotConfig`, finds the nearest converged solution
  (cache or background solve), and shows per-decision EV loss, an EV graph, and
  tags. Unmatched lines are flagged `no_reference`.

## 14. API Surface (initial)

- `GET/POST /api/spots`, `POST /api/spots/:id/solve`
- `GET /api/solutions/:id`, `GET /api/solves/:id/events` (SSE)
- `GET /api/farm/status`, `POST /api/farm/pause`, `POST /api/farm/resume`
- `GET /api/preflop/charts`, `GET /api/preflop/quiz`
- `GET/POST /api/ranges`
- `POST /api/hands/parse`, `GET /api/hands/:id`, `POST /api/hands/:id/review`
- `POST /api/trainer/session`, `POST /api/trainer/answer`
- `GET /api/simulator/hand`, `POST /api/simulator/action`
- `GET /api/curriculum`, `GET /api/curriculum/:slug`, `GET /api/daily-plan`
- `GET /api/stats/overview`, `GET /api/stats/leaks`

## 15. Testing Strategy

- **Unit (Vitest)**: `core` (cards, ranges, pot/EV math), HH parser, spot
  canonicalization + hashing, scoring, SM-2 scheduling.
- **Integration**: solver adapter parsing against a small fixture solution;
  cache hit/miss; queue resume after restart; convergence gate excludes
  non-ready solutions.
- **Golden**: known preflop/postflop spots -> expected frequencies within tolerance.
- **E2E (Playwright)**: preflop trainer flow, explorer flow, simulator hand flow.
- **Verify command**: `./run.sh verify` (typecheck + tests + build).

## 16. Phasing

Each phase is implemented via its own plan.

- **P0**: TexasSolver CLI/output spike; monorepo skeleton; `core`; `db` schema.
- **P1**: Solver orchestrator + cache + solve farm + preflop precompute.
- **P2**: Preflop chart trainer (instant value; no postflop solve needed).
- **P3**: Range builder.
- **P4**: Postflop spot explorer.
- **P5**: In-hand trainer + simulator (table UI, GTO bots, grading).
- **P6**: Coaching engine + curriculum + daily plan + progress/leaks + spaced repetition.
- **P7**: Hand history review.
- **P8**: Polish (settings, shortcuts, export/import, performance, docs).

## 17. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| TexasSolver CLI/output format differs from assumptions | High | Phase 0 spike validates the adapter before dependent work |
| Solve cost too high for smooth UX | High | Persistent cache, farm, priority queue, progress UI |
| Multiway postflop not gradable | Medium | `no_reference` handling; grade HU/preflop only |
| Coverage gaps frustrate training | Medium | Coverage planner + night mode; modules show precompute progress |
| Numerical parity with commercial products expected | Medium | Explicitly out of scope; define "GTO-accurate" (section 1.3) |
| Storage growth from many solutions | Low | Compressed payloads; configurable retention/eviction |
| Farm starves interactive use | Medium | Priority queue; yield on interactive jobs; night mode |

## 18. Future Extensions

- ICM / tournament-equity engine via `SolverEngine` extension point.
- Exploitative / population opponent mode and exploit scoring.
- Multi-user accounts and cloud/remote access.
- AI coach with natural-language explanations.
- Push/fold and other short-stack specialized modules.
