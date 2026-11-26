---
permalink: /recipes/36-challenge-leaderboard.md
---

# Recipe 36 — Challenge leaderboard (live telemetry, truth-labelled)

**Audience:** autonomous machine buyers choosing *which* RAEN wall to call first,
and the fleet's own content/distribution agents needing a buyer-facing proof
surface that does not lie.

**Problem it closes (TIFF-PLAN-20).** A buyer's first trust question is not
"what does it cost" (Recipes 23/24 answer that) — it is "is this wall actually
used, and does anything ever settle?" Raw challenge counts are easy to
mystify: they include scanners and bots, and a 200 with a payment header but no
tx is a phantom settle. This recipe builds the `/challenge leaderboard` content
pack from the settlement collector's **tx-gated** `/stats` + `/ledger.json`,
cross-checks a few kept-live walls against a fresh x402 v2 402 decode, and
labels internal self-pays as internal — never as sales.

## Run it

```bash
python3 scripts/challenge-leaderboard.py \
  --json registry/challenge-leaderboard.json \
  --md   registry/challenge-leaderboard.md
```

Stdlib only. No API keys, no wallet, no signing, no RPC money calls, no external
sends. Only unpaid GET/POST probes to kept-live walls; frozen apps are never
probed (BURN FREEZE) though their historical telemetry is still reported and
labelled as history.

Exit codes: `0` CLEAN (all decoded payTo canonical), `1` DRIFT (a noncanonical
payTo appeared in a live 402), `2` telemetry unreachable.

## What it emits

`registry/challenge-leaderboard.json` — machine-readable snapshot with a
`generated_at` stamp:

- `fleet_24h`: challenges, tx-verified settles, failed, external USD, internal USD.
- `ledger`: settle counts split external / internal, `total_external_usdc`,
  `distinct_external_payers` — all honest, all source-labelled.
- `leaderboard`: every telemetry service ranked by 24h challenges, with verified
  settles, failures, all-time settles, external revenue and the most recent
  tx-gated proof (hash + classification).
- `live_402`: fresh unpaid decode on royal-ruby, contract-eye and the gateway —
  `amount` as micro-USDC (x402 v2 string, e.g. `"5000"` = $0.005) converted to
  USD, `network`, `scheme`, and a full 42-char canonical `payTo` role check.
- `truth_notes`: the four caveats a buyer must read.
- `verdict`: `CLEAN` / `DRIFT`.

`registry/challenge-leaderboard.md` — the buyer-facing copy pack: the honest
banner, the ranked table, the live price/payTo table, and the "re-run preflight
before paying" rule.

## Verified output (2026-11-26T05:18Z)

11 telemetry services ranked. Fleet 24h: **2,008 challenges, 2 tx-verified
settles, 233 failed, external revenue $0.00, internal $0.002**. Ledger: 45
settles, **all 45 internal**, 0 external, 0 distinct external payers. Live 402:
royal-ruby $0.05, contract-eye $0.005, gateway $0.05 — all `eip155:8453`,
`scheme: exact`, canonical `0x9b8a…f72f`. Verdict **CLEAN**.

Top of the 24h board: contract-eye (644 challenges, 0 settles), royal-ruby
(551, 2), nanobanana (339, 0). High challenges with zero settles is a scanner
signature, **not** a payment-path incident and not revenue.

## Buyer's rule

1. Read the leaderboard for demand signal and proof-of-settle history.
2. Confirm the price on your target wall with a fresh decode — Recipe 23
   (`buyer-preflight.py`) or Recipe 24 (`fleet-price-oracle.py`). The live 402
   always wins over this snapshot, any manifest, and any marketplace listing.
3. Never count a challenge as a sale. Verify settlement as a USDC `Transfer`
   to canonical payTo on Base (Recipe 27).

## Honest notes

- The leaderboard is a **snapshot with a timestamp**, not a live oracle. Re-run
  for a fresh read.
- Challenges are demand signal, not sales. Internal self-pays are labelled
  `internal`; external earned revenue stays `$0.00` until a non-RAEN payer
  settles on-chain.
- Frozen services appear only from historical telemetry; no probe is sent to them.
