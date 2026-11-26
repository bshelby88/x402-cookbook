# RAEN /challenge leaderboard — live, truth-labelled

Generated 2026-11-26T05:18:57.673617+00:00. Source: settlement-collector `/stats` + `/ledger.json` (tx-gated), cross-checked against a fresh x402 v2 402 decode on kept-live walls.

> **Read this first.** Challenges include scanners and bots — they are a demand signal, not sales. Only settlements with an on-chain tx count. **External earned revenue: $0.00.** All 45 verified settles are internal self-pays from the AgentCash test wallet, labelled as such, never counted as revenue.

Fleet 24h: **2008 challenges**, 2 tx-verified settles, 233 failed. External USD 0 / internal USD 0.002.

## Challenge leaderboard (24h, live telemetry)

| # | wall | challenges 24h | verified settles 24h | failed 24h | all-time settles | external $ | last proof tx |
|---|------|---------------:|---------------------:|-----------:|-----------------:|-----------:|---------------|
| 1 | contract-eye | 646 | 0 | 6 | 6 | 0.00 | `0xa677d8d101…` (internal) |
| 2 | royal-ruby | 552 | 2 | 47 | 38 | 0.00 | `0xe052a46487…` (internal) |
| 3 | nanobanana | 339 | 0 | 26 | 0 | 0.00 | — |
| 4 | nft-alpha | 101 | 0 | 7 | 0 | 0.00 | — |
| 5 | vault-pro | 91 | 0 | 32 | 0 | 0.00 | — |
| 6 | dispatch | 85 | 0 | 5 | 0 | 0.00 | — |
| 7 | dispute-forge | 54 | 0 | 59 | 0 | 0.00 | — |
| 8 | escrow | 50 | 0 | 5 | 0 | 0.00 | — |
| 9 | tradingagents | 46 | 0 | 26 | 0 | 0.00 | — |
| 10 | sentry-forge | 44 | 0 | 20 | 0 | 0.00 | — |
| 11 | raen-facilitator-worker | 0 | 0 | 0 | 1 | 0.00 | `0x428ddc362a…` (internal) |

## Live 402 price + payTo (fresh, unpaid probe)

| wall | HTTP | price | payTo role | network |
|------|------|------:|------------|---------|
| royal-ruby | 402 | $0.05 | CANONICAL | eip155:8453 |
| contract-eye | 402 | $0.005 | CANONICAL | eip155:8453 |
| gateway | 402 | $0.05 | CANONICAL | eip155:8453 |

Verdict: **CLEAN**.

Buyer rule: re-run `buyer-preflight.py` on your target wall immediately before paying. The live 402 is authoritative; this leaderboard is a snapshot with a timestamp.
