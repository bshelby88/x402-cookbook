# 54. Settlement Dependability Grader — will my payment actually settle?

**Read-only, stdlib-only, no signing, no X-PAYMENT, no deploy, no funds.**

The first 53 tools grade the wall, the manifest, the schema, the payer wallet, the
collector ledger or the chain. None answers the question an autonomous buyer asks
*before it integrates*: "if I pay this wall, will my payment actually settle on-chain,
and how long will it take?" A canonical 402 is a promise; a proven settlement path is
a track record. This tool grades the track record from the collector's own
chain-verified settlement telemetry (`/stats.services`, `24h` and `all` windows) and
publishes a buyer-facing dependability card. It is the reliability signal that turns
"we have a paywall" into "we have a paywall that pays through."

## Why this is an acquisition tool

A machine buyer cannot file a support ticket or chase a refund. It chooses APIs it
can pay deterministically. Two facts decide that choice:

1. **Does the path actually settle?** Only `settled_verified` counts — the collector
   gates `settled` on an on-chain tx hash (TRUTH law, 2026-11-11). Internal test
   settles prove the *rails* work (same USDC/EIP-3009 path) but are never revenue.
2. **How fast?** `p95_ms` settle latency: above 15 s an autonomous caller that waits
   for confirmation starts hitting its own timeouts.

## The grades

| Grade | Verdict | Meaning for a buyer |
|---|---|---|
| `A` | `PROVEN_FAST` | Chain-verified settles, p95 ≤ 15 s, failure rate < 10% — safest to integrate. |
| `B` | `PROVEN_DEGRADED` | Settles, but p95 > 15 s and/or failure rate ≥ 10% — works, budget latency. |
| `C` | `UNPROVEN_NO_PAYER` | 0 settles, low failure rate — path untested, not broken. No buyer has proven it yet. |
| `D` | `SCANNER_NOISE` | 0 settles, ≥20% failure rate — scanner/probe traffic, NOT an incident. |
| `?` | `TELEMETRY_BLIND_SPOT` | Paid wall absent from collector telemetry — no dependability data exists. |

The `D`/`C` distinction is deliberate. Skill doctrine: high challenge volume with
zero settles often means bots/scanners, not a payment-path incident. A tool that
cried "outage" on every 0-settle wall would be worse than useless — it would bury
the two walls that actually settle in a sea of false alarms. `SCANNER_NOISE` says
"no genuine payer yet"; it never says "broken".

## 2026-11-27 live run (12:43Z)

```
verdict OK   buyer walls proven path 2/4   canonical 402 4/4   drift 0
fleet 24h: 2989 challenges / 14 settled (14 verified) / 111 failed / p50 8871ms / p95 17749ms
honest external earned $0.00 (collector $0.012 = breadth-crawler dust, tools 50/51)
```

| Wall | Price | Grade | Verdict |
|---|---|---|---|
| contract-eye | $0.005 | A | `PROVEN_FAST` — 3 verified settles, p95 5330ms |
| royal-ruby | $0.005 | B | `PROVEN_DEGRADED` — 5 verified settles, p95 16371ms |
| nanobanana | $0.01 | C | `UNPROVEN_NO_PAYER` — 0 settles in 24h and all-time |
| raen-mcp-gateway | $0.005 | ? | `TELEMETRY_BLIND_SPOT` — paid wall absent from `/stats.services` |

Fleet context (all services, frozen tagged): `shipgate402` grade B (`PROVEN_DEGRADED`,
6 verified settles, p95 17749ms); every frozen app is C or D — none is a new
incident, and the freeze is respected (telemetry read only, no restart).

**Gateway price resolution:** a prior cycle reported the gateway at $0.05 (50000
atoms, owner-gated ladder drift). This run decodes **5000 atoms / $0.005** with the
full canonical payTo — the owner-approved ladder. Two Fly releases landed at
12:41:14Z and 12:42:27Z, immediately before this probe, so a concurrent agent
deploy restored the approved price. Pricing is owner-gated; no price change was
made by this tool. Do not deploy over a peer's active lease.

## Snapshots

- `registry/settlement-dependability.json` — full live snapshot (buyer cards + fleet telemetry).
- `registry/settlement-dependability.md` — buyer-facing card.

## Truth and scope

`--check` exits non-zero only on a canonical-payTo break (never on a grade C/D — a
missing payer is not a defect). Live 402 decode is authoritative over the snapshot
timestamp. Frozen walls are reported, never restarted. Honest external earned stays
**$0.00**; internal settles prove the path, not demand.
