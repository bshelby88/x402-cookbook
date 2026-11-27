# 52. Chain Ledger Reconciler — money truth from the chain, not the collector

**Status:** live, read-only. No signing, no X-PAYMENT, no funds movement, no deploys.

## The gap

Tools 50 (`demand-signal.py`) and 51 (`breadth-detector.py`) both read the
settlement-collector's `/ledger.json`. That means both inherit the collector's
blind spots. On 2026-11-27 this caused a real disagreement between two agents
looking at the same payer:

- One called `0x171d8021…50fca` a "genuine external machine buyer" (3 calls / 2 services in ~50s).
- The other called it breadth-crawler dust.
- Both were reading the collector, which reported `revenue_external_usd=$0.012`
  while `total_crawler_usdc=0`, and omitted a chain-real $0.10 settle entirely.

Neither tool can see a payment that is on chain but absent from the ledger.
The owner's law is **money truth = chain**, so the collector cannot be the
final authority on what was paid.

## What it does

`chain-reconciler.py` reads canonical USDC **inflows straight from Base** and
reconciles them against the collector ledger:

1. `eth_getLogs` on Base USDC, `topics[0]=Transfer`, `topics[2]=canonical`,
   over a ~120k-block lookback in 20k chunks (publicnode-safe).
2. For each inflow: classify the sender as `INTERNAL` (full-address facts),
   `BREADTH_CRAWLER` (tool 51's behaviour-discovered registry), or `EXTERNAL`.
3. Match each inflow tx against the collector ledger:
   - on chain, not in ledger → `blinded_spot` (a payment the collector missed)
   - in ledger, not on chain in window → reported, count only (window may be shorter)
4. Publish `genuine_external_earned_usd` = external chain inflows minus
   breadth-class payers, and flag unlogged external inflows as buyers the
   fleet would otherwise fail to see.

This is distinct from tool 51: that scans a payer's **outflows** to discover
breadth; this scans canonical's **inflows** to audit the collector. Together
they close both ends of the attribution chain.

## Live verdict (2026-11-27, current block 62922629)

- Chain inflows to canonical in lookback: **4, totaling $0.115** (0 chunk errors)
- $0.005 internal (AgentCash, logged)
- $0.11 breadth-crawler `0x171d8021…50fca`: $0.005 + $0.005 logged,
  **$0.10 chain-real but UNLOGGED** by the collector
- Genuine external earned: **$0.00 (honest)**

The $0.10 "unrecorded" payment cited as a possible first buyer was a direct,
payer-signed EIP-3009 transfer from a breadth-scatter crawler — chain-real,
not demand. `py_compile` OK, live run reproducible.

## Usage

```sh
python3 scripts/chain-reconciler.py                 # live run -> registry/chain-reconciler.json
python3 scripts/chain-reconciler.py --check         # verify snapshot reproducible
python3 scripts/chain-reconciler.py --address 0x...  # classify one sender standalone
```

Exit: 0 report emitted, 1 fetch error.

## Boundaries

Read-only, stdlib-only. No signing, no X-PAYMENT header, no funds movement,
no external sends, no directory POSTs, no deploys, no secrets. Frozen apps are
never touched. Internal-wallet and breadth facts are read from repo truth,
never from memory shorthand (homoglyph addresses exist).
