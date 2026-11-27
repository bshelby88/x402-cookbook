# 51. Breadth-Crawler Detector — discover dust-scatter payers without a hardcoded list

**Status:** live, read-only. No signing, no X-PAYMENT, no funds movement, no deploys.

## The gap

The settlement-collector books any non-internal payer as `external`. Two real
breadth-class crawlers have been misbooked as external revenue:

- `0xc9c7b38c0942914fc8ea12063bc92dcd3b581670` — TIFF-BUYER-05 (156 payees / 6.4d, p50 $0.003)
- `0x171d8021b98c53dcbb3c9c30cbbbeb1b01850fca` — discovered 2026-11-27 (40+ transfers / 18+ recipients / ~29 min burst)

Tool 50 (`demand-signal.py`) re-excludes crawlers from a **recorded list**. That
cannot keep up: a new crawler appears, and `revenue_external_usd` silently
inflates until a human adds the address. The owner's objective is autonomous
operation with zero human intervention, so the exclusion must be **discovered**,
not maintained.

## What it does

`breadth-detector.py` classifies every external payer in the collector's
`/ledger.json` from **on-chain behaviour** alone:

1. Read `GET /ledger.json` and `GET /stats` (public, no auth).
2. For each `classification=external` payer, scan Base USDC `Transfer` logs
   with `topics[1] = payer` over a ~200k-block lookback (~14h), in 40k chunks
   (publicnode rejects >50k-block `eth_getLogs`).
3. Compute outgoing transfer count, distinct recipients, and burst span
   (block timestamps). State lookback coverage explicitly — never claim a
   bare "zero".
4. Flag `BREADTH_CRAWLER` when a payer has **>=8 distinct recipients** (breadth)
   or **>=15 transfers inside 60 minutes** (burst). Otherwise `GENUINE_PAYER`.
5. Report `honest_external_earned_usd = collector_reported_external - crawler_usd`.

Both signals are needed: `0xc9c7` is slow breadth (114 tx / 35 recipients /
~6h), `0x171d` is a fast burst (41 tx / 20 recipients / ~33 min). One threshold
alone misses one of them.

## Live verification — 2026-11-27

- Collector `revenue_external_usd_24h = $0.012` (2 external payers).
- `0x171d8021…50fca`: 41 transfers, 20 recipients, 32.9-min span → `BREADTH_CRAWLER` (breadth + burst).
- `0xc9c7b38c…1670`: 114 transfers, 35 recipients, 361.6-min span → `BREADTH_CRAWLER` (breadth).
- Verdict `CRAWLER_NOISE`, genuine payers `[]`, **honest external earned = $0.00**.
- `py_compile` OK; `--check` → `CANONICAL` on a fresh live re-run.

On-chain attribution this run: canonical +0.115 Base = 0.005 internal (AgentCash)
+ 0.11 breadth-scatter from `0x171d…50fca` (0.005 royal-ruby + 0.005
contract-eye price-tiered calls plus a 0.1 direct transfer, all in the same
28-min burst). The 0.1 has no collector entry and matches no price tier —
scatter, not revenue. Both payments are EIP-3009 (relayer-submitted, payer-signed).

## Honesty / limits

- Partial lookback is stated per payer; a payer inactive in the window may be
  under-counted. Thresholds are heuristic, published in the registry JSON.
- This grades **payers**, not walls. It does not sign, pay, deploy, or move funds.
- Money truth = chain. Coordination truth = Library. Code truth = GitHub.

## Handoff

- `[staci]` / `[kip]` Port this behavioural exclusion into the collector so
  `/stats revenue_external_usd` is honest without a manual address list
  (deploy-lane, freeze-legal for kept-live).
