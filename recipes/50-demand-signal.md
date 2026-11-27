# 50. x402 Demand Signal / Repeat-Buyer Monitor

**Status:** live, read-only. No signing, no X-PAYMENT, no funds movement, no deploys.

## The gap

The owner KPI is **repeat buyers × calls/payer**, and money truth is the chain.
The other 49 cookbook tools grade the wall (preflight, conformance, price),
the docs (schema parity, llms-lint), the wallet (wallet-fit), or the post-payment
receipt (receipt-verifier). None of them answers the acquisition question that
actually drives the MONEY law: **is there any real demand, and is it repeating?**

The settlement-collector publishes a verified ledger (`/ledger.json`) and 24h
stats (`/stats`). Its `revenue_external_usd` figure counts any non-internal
payer as external — including breadth-class crawler dust. That produced a
misleading `$0.002` "external revenue" line from payer
`0xc9c7b38c0942914fc8ea12063bc92dcd3b581670` (TIFF-BUYER-05: 156 payees / 6.4d,
p50 $0.003) — a real on-chain transfer, but not a customer and not demand.

`demand-signal.py` re-derives the honest signal from the verified ledger.

## What it does

- Reads the collector's public `GET /stats` + `GET /ledger.json` (no auth).
- Classifies every settled tx: internal test traffic, breadth-class crawler
  (known-address re-exclusion), genuine external, or other.
- Computes the KPI inputs: **distinct genuine external payers**, **repeat buyers**
  (payer with >1 call), **calls per payer**, per-service demand, and
  **honest external earned USD** (chain-verified, non-crawler).
- Optional `--live` cross-reference: one UNPAID 402 probe per kept-live paid
  wall, decoded for scheme / network / full canonical payTo / integer `amount`.
  Frozen apps are never touched.
- Verdict: `EVIDENCE_DEAD` (0 genuine external payers) · `SINGLE_BUYER` ·
  `REPEAT_SIGNAL` (>=1 repeat buyer).

## Honest result at ship (2026-11-27)

```
VERDICT: EVIDENCE_DEAD
honest external earned USD: $0.000000
genuine external payers: 0 | repeat buyers: 0
crawler dust USD (excluded): $0.002000
classification counts: {'internal': 55, 'external': 1, 'crawler': 0? -> re-excluded below}
```

(The shipped tool folds the single external tx into `crawler` by payer address,
so its `classification_counts` shows `crawler: 1`, `external: 0` — the honest
reading: 55 internal test settles + 1 breadth-crawler dust transfer, **zero
genuine external payers**.)

Live unpaid 402 cross-reference — all four walls canonical, `exact`,
`eip155:8453`, full 42-char canonical payTo:

| wall | live price |
|---|---|
| royal-ruby `/api/law-lookup` | $0.005 (5000 atoms) |
| contract-eye `/api/analyze-contract` | $0.005 (5000 atoms) |
| nanobanana `/api/generate-image` | $0.01 (10000 atoms) |
| shipgate402 `/v1/ship-check/batch` | $0.002 (2000 atoms) |

A healthy paid path with **zero demand** is the honest state. Do not misread
crawler dust as a customer; do not report $0.002 as earned revenue.

## Usage

```
python3 scripts/demand-signal.py
python3 scripts/demand-signal.py --out registry/demand-signal.json
python3 scripts/demand-signal.py --no-live
```

Exit: `0` = report emitted · `1` = fetch error · `2` = no ledger transactions.

## Safety

Read-only, stdlib-only. Reads only public GET surfaces plus unpaid 402 probes.
Never signs, never attaches an X-PAYMENT header, never pays, never moves money,
never sends externally, never touches a frozen app, stores no secrets.
