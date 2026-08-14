# AGENTS.md — Hướng dẫn tiếp tục dự án GTO Poker Trainer

> **Tài liệu này dành cho AI agent (model free) tiếp tục dự án khi session trước hết context.**
> Người dùng nói **tiếng Việt** — trả lời bằng tiếng Việt, code/comment giữ tiếng Anh.

## 1. Mục tiêu dự án

Phần mềm luyện tập poker GTO (NLHE tournament/MTT) cho **heads-up confrontations**:
solver CFR tự viết + trainer (CLI). Vị trí: `/home/tuanlinh/poker`.

Stack: Python 3.12, venv tại `.venv/bin/python` (numpy 2.5.2, pytest).
**Luôn dùng `.venv/bin/python`** (pip hệ thống bị chặn bởi PEP 668).
Chip: `BB=100, SB=50`; hiển thị EV theo bb (chips/100).

## 2. Trạng thái hiện tại (đã commit)

- **Hoàn thành & đã test (46 tests pass)**: `gto/cards.py` (evaluator Cactus Kev),
  `gto/ranges.py` (Range 1326 combos), `gto/game.py` (betting tree),
  `gto/solver.py` (MCCFR). Chạy: `timeout 115 .venv/bin/python -m pytest -q`
- **Push/fold models ĐÃ PRE-SOLVE** tại `solutions/` (gitignored):
  `pushfold_10bb.pkl`, `pushfold_15bb.pkl`, `pushfold_20bb.pkl`
  (60k iterations mỗi cái; SB shove 59%/46%/39%, BB call 37%/26%/19% — hợp lý, hội tụ <0.5bb theo BR chính xác)
- **Full tree 100bb (585 nodes) mới giải tới ~50k iterations**:
  `solutions/full100_sb_bb_50k_checkpoint.pkl` (63MB) — **CHƯA HỘI TỤ**
  (exploitability ≈ 82bb, 72o còn raise 80%). Cần tiếp tục (xem mục 6).
- `solutions/`, `.venv/` nằm trong `.gitignore` (model lớn không commit).
- Git: 5 commits đã lưu, nhánh `main`.

## 3. Kiến trúc & quy ước (BẮT BUỘC đọc trước khi sửa)

### gto/cards.py
- Card = int 0..51: `rank = card//4` (0=2 .. 12=A), `suit = card%4` (c,d,h,s).
  Ví dụ: 48=Ac, 49=Ad, 50=Ah, 51=As.
- Strength 1..7462 (dense). Khoảng category: 1-1277 high, 1278-4137 pair,
  4138-4995 two pair, 4996-5853 trips, 5854-5863 straight, 5864-7140 flush,
  7141-7296 full house, 7297-7452 quads, 7453-7462 straight flush (royal=7462).
- `evaluate_7_batch(hands (N,2), board (5,))` — **1 board mỗi lần gọi**; hand
  trùng card với board → 0. Không gọi với (N,5) board — sai kết quả!

### gto/ranges.py
- `COMBOS` (tuple 1326), `COMBO_INDEX` dict, `NUM_COMBOS=1326`.
- Ký pháp GTO Wizard: `KQo+` = KQo,AQo,AKo (36); `ATs+`; `22+`.
  `_base_combo`, `_combo_cards`, `_plus`, `_between` — đừng gọi với ký pháp lạ.

### gto/game.py
- `GameConfig`: `stack` (chips), `bet_sizes`/`raise_sizes` per street (phân số pot),
  `push_fold` (SB: fold/shove; BB: fold/call — dành cho MTT push/fold).
- `raise_to = pot + to_call + int(frac * last_bet)` (last_bet = inv[opp]);
  `bet_amount = int(frac * pot)`; `stacks = (stack - pot + inv[1], stack - pot + inv[0])`.
- `build_tree(cfg, start_street, start_pot, start_inv)` → `(nodes dict, root_key)`.
  Node key: `(street, pot, inv0, inv1, to_act)`. Terminal nodes MANG `inv`
  (đã sửa — cần thiết cho payoff net).
- **Payoff phải là NET** (pot − đóng góp của mình), không phải gross.

### gto/solver.py
- `SolverConfig`: iterations, seed, ranges, board, start_pot/start_inv, payoff.
- MCCFR external sampling: mỗi iteration sample 1 hand opponent (weighted theo
  range, tránh dead cards) + 1 runout; traverser xen kẽ `it % 2`; tại node của
  traverser liệt kê MỌI action tính vector giá trị trên 1326 hands; node opponent
  sample 1 action. Regret update: `reg += opp_reach * (vals - v)`; `strat_sum += strat`.
  **KHÔNG đổi sang scalar per-hand sampling** (hội tụ rất tệ, đã thử và bỏ).
- `_terminal_vec`: net payoff + **blocker correction** (xem mục 4).
- `strategy`/`avg_strategy`: regret matching / trung bình, vector (1326, n_actions).
- `strategy_for_hand(key, player, "AKs")`: trung bình theo suit variants.
- `save(path)`/`load(path)`: pickle **cả regrets + strat_sum** (đã sửa) — dùng
  để resume: `s = Solver(cfg, scfg); s.load(path); s.solve(...)`.
- `exploitability(trials, boards_per_trial)`: ước lượng BR — **chỉ là monitor,
  có noise/bias nhỏ**; để đo chính xác dùng equity matrix Monte Carlo
  (board uniform: `rng.choice(52, 5, replace=False)` — KHÔNG dùng `rng.choice(52,4)`
  rồi lấy prefix — nó trả về sorted → board thiên về lá thấp!).
- Tốc độ: push/fold ~683 it/s; full tree ~86 it/s. `strengths(board)` cache tối đa 4000 boards.

## 4. Các bug ĐÃ SỬA (không được tái phạm!)

1. **Gross vs net payoff**: `_terminal_vec` từng trả ±pot (fold = −1600 thay vì
   −100) → BB "đúng" khi call mọi thứ. Sửa: net = pot − contrib; fold mất đúng
   blind; terminal nodes phải giữ `inv`.
2. **Sign flip p=1**: từng `if p==1: out = -out` — sai vì vector đã là của traverser.
3. **Blocker bias**: board sample trừ hand opponent; hand hero trùng card board
   bị tính thua (−1500) thay vì impossible (0) → mọi hand bị bias ~20%.
   Sửa: blocked → 0, và chia cho `p_avoid = C(d-2,t)/C(d,t)` với `d = 52 − board0 − 2`,
   `t = 5 − board0` (d=50 preflop → p_avoid≈0.80816).
4. **Jensen bias trong exploitability**: max(action) TRƯỚC khi average → ước lượng
   cao. Sửa: trả vector per-action, average trước, max sau. Ở opponent node dùng
   broadcast-sum `(2,N)+(1,N)` hợp lệ; chỉ collapse bằng max khi shape không
   broadcast được (bug (3,N)+(2,N)).
5. **save/load mất regrets** → không resume được. Đã lưu đủ 4 mảng.
6. Test tôi viết từng sai: card 48 là Ac (không phải As); `rng.choice(52,4)`
   trả sorted. Cẩn thận khi assert.

## 5. Lệnh hữu dụng

```bash
cd /home/tuanlinh/poker
timeout 115 .venv/bin/python -m pytest -q          # 46 tests
timeout 115 .venv/bin/python -u -c "..."           # script ngắn (-u: unbuffered)
# Xem strategy của model đã lưu:
timeout 60 .venv/bin/python -u -c "
from gto.game import GameConfig
from gto.solver import Solver, SolverConfig
s = Solver(GameConfig(stack=1500, push_fold=True), SolverConfig(iterations=1))
s.load('solutions/pushfold_15bb.pkl')
print(s.strategy_for_hand(s.root_key, 0, 'AA'))"
```

Lưu ý shell: tool bash tự kill lệnh > 120s — bọc `timeout` và dùng tham số
timeout của tool (tối đa ~600s). Chạy dài phải **chunk + save_every** (mục 6).

## 6. Việc cần làm tiếp theo (theo thứ tự)

1. **TIẾP TỤC SOLVE full tree 100bb** (cần thiết cho trainer preflop):
   ```bash
   timeout 580 .venv/bin/python -u -c "
   from gto.game import GameConfig
   from gto.solver import Solver, SolverConfig
   s = Solver(GameConfig(), SolverConfig(iterations=25000, seed=1, report_every=10**9))
   s.load('solutions/full100_sb_bb_50k_checkpoint.pkl')
   s.solve(verbose=False, save_every=10000, save_path='solutions/full100_sb_bb_50k_checkpoint.pkl')
   s.save('solutions/full100_sb_bb_50k_checkpoint.pkl')"
   ```
   Lặp lại cho tới ~300-500k iterations (mỗi chunk +25k ≈ 5 phút; ~86 it/s).
   Hội tụ khi `exploitability(trials=25, boards_per_trial=10)` < ~2000 và 72o fold > 80%.

2. **`gto/icm.py`**: Malmuth–Harville (đệ quy + memo) — `icm_equities(stacks, payouts)`.
   Hook vào solver qua `SolverConfig.payoff` (đã có `_terminal_icm` skeleton
   trong solver.py — xem signature `fn(p, pot, hero_wins, villain_wins, node, cfg)`).
   Spot chuẩn: 8-max final table, payouts [40,25,15,10,5,3,2,1]% hoặc MTT 9-max.

3. **Trainer engine** (`gto/trainer/`): 
   - Push/fold ICM quiz: nạp model từ `solutions/`, hỏi "SB shove/fold? với tay X, 15bb",
     chấm điểm theo strategy GTO, hiện EV.
   - Preflop spot (BU vs BB / SB vs BB 2.5x) dùng full tree model.
   - **Postflop theo board**: tree hiện tại cho strategy TRUNG BÌNH theo board —
     không dùng được cho "flop cụ thể". Cần solve subgame riêng: `SolverConfig(board=...,
     start_street=1, start_pot, start_inv)` rồi solve on-demand (~vài phút) hoặc cache.
4. **CLI trainer** (`gto/cli.py`, entry point `gto-trainer` đã khai trong pyproject).
5. **README** (đừng tự tạo nếu chưa được yêu cầu rõ).

## 7. Ghi chú kiến thức poker (để đánh giá kết quả)

- Push/fold 15bb (không ante) chuẩn: SB shove ~60%, BB call ~28% (kết quả của
  solver: 46%/26% — hơi chặt nhưng đúng hướng, BR chính xác <0.5bb).
- Stack càng sâu → SB shove càng ít, BB call càng ít (10bb: 59/37, 20bb: 39/19 ✓).
- AA/AKs luôn shove; 72o/K2s luôn fold; A5s/22 gần biên giới.

## 8. Điều quan trọng về workflow

- **Luôn lưu trạng thái**: model lớn giải theo chunk (save_every + load resume)
  để không mất công khi timeout/đổi model.
- Commit sau mỗi milestone đáng kể (`git add -A && git commit`).
- Nếu cập nhật file này, hãy giữ nó ngắn gọn và chính xác.
