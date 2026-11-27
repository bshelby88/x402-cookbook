# Chain Ledger Reconciler — buyer card

**Question answered:** "Did the collector miss any payment, and is any of it real demand?"

The collector ledger is a secondary source. Money truth is the chain. This tool
reads canonical USDC inflows directly from Base and reconciles them against the
collector, so a chain-real payment the collector never logged cannot be
silently reported as "no revenue" — and cannot be over-claimed as demand either.

## Live verdict (2026-11-27, block 62922629)

- Chain inflows to canonical (lookback): **4 / $0.115**, 0 chunk errors
- Internal (AgentCash): **$0.005**, logged
- Breadth-crawler `0x171d8021…50fca`: **$0.11**
  - $0.005 + $0.005 logged (collector booked these as `external`)
  - **$0.10 chain-real but UNLOGGED — collector blind spot**
- **Honest external earned: $0.00**

## Why this matters for acquisition

The $0.10 unlogged transfer was cited as a possible "first repeat machine
buyer". Chain reconciliation shows it is a direct payer-signed EIP-3009 scatter
from a behaviour-discovered breadth-crawler — chain-real, but not demand.
Acquisition effort should follow genuine external payers, and this tool makes
sure the fleet can actually see them (and cannot invent them).

## Method (public, reproducible)

`eth_getLogs` on Base USDC (`topics[0]=Transfer`, `topics[2]=canonical`) over a
~120k-block lookback in 20k chunks; classify each sender against full-address
internal facts + tool 51's breadth registry; match tx hashes to collector
`/ledger.json`. Thresholds and full inflow list in
`registry/chain-reconciler.json`.

```sh
python3 scripts/chain-reconciler.py
python3 scripts/chain-reconciler.py --address 0x...
```

Read-only, stdlib-only, no signing, no funds, no deploy.
