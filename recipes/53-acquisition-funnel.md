# 53. Machine-Buyer Acquisition Funnel Auditor

**Read-only, stdlib-only, no signing, no X-PAYMENT, no deploy, no funds.**

The first 52 tools each grade one face of the fleet — the wall, the manifest, the
OpenAPI schema, the payer wallet, the collector ledger, the chain. None answers the
question the owner actually asks: *can an autonomous agent find us, understand us,
pay us, and come back?* This tool fuses those faces into one per-wall funnel and
names the single biggest acquisition blocker. It is the acquisition-layer analogue
of a conversion funnel, computed entirely from live read-only probes plus the
accumulated evidence artifacts (41/43/47/48/50/51/52).

## The four stages

| Stage | Live question | Source of truth |
|---|---|---|
| `DISCOVER` | Is this wall listed in the machine catalog an agent browses? | `rae-fleet-router.fly.dev/catalog.json` |
| `UNDERSTAND` | Does `/.well-known/x402.json` name the canonical payTo and declare request fields? | live manifest |
| `PAY` | Does an unpaid POST return a canonical x402 v2 challenge (`exact`, `eip155:8453`, full canonical payTo)? | live decoded 402 header |
| `REPEAT` | Does the collector ledger show a genuine external settle for this service? | collector `/ledger.json`, internal + breadth-crawler payers excluded |

A wall is `READY` only if all four stages pass. Otherwise the verdict is
`BLOCKED_AT_<STAGE>` — the FIRST failing stage, because a machine buyer cannot
reach a later stage without clearing the earlier one.

## Why the exclusions matter (TRUTH law)

`REPEAT` deliberately excludes the canonical wallet, the retired wallet, AgentCash
(internal test traffic, never revenue) and the two behaviour-discovered
breadth-class crawlers (`0xc9c7b38c…1670`, `0x171d8021…50fca`). Those crawlers scatter
sub-cent payments across hundreds of payees; the collector misbooks them as
`revenue_external_usd`. Counting them as "repeat buyers" would be the exact false
demand signal tools 50–52 were built to kill. Full-form addresses only: 42-char
constants, no shorthand, homoglyph-poison safe.

## 2026-11-27 live run (05:30Z)

```
catalog HTTP 200   walls_ready 0/4   honest_external_earned_usd 0.0

royal-ruby           BLOCKED_AT_REPEAT    discover ✓  understand ✓  pay ✓ ($0.005)  repeat ✗
contract-eye         BLOCKED_AT_DISCOVER  discover ✗  understand ✓  pay ✓ ($0.005)  repeat ✗
nanobanana           BLOCKED_AT_REPEAT    discover ✓  understand ✓  pay ✓ ($0.01)   repeat ✗
raen-mcp-gateway     BLOCKED_AT_DISCOVER  discover ✗  understand ✓  pay ✓ ($0.05)   repeat ✗
```

**Verdict:** the acquisition funnel is not closed for any kept-live wall, but for
two different reasons. `royal-ruby` and `nanobanana` clear discovery, docs and
payment — their only missing stage is a *genuine returning buyer*. `contract-eye`
and the `raen-mcp-gateway` are blocked earlier: they are **absent from the router
catalog**, so an agent browsing the fleet's machine catalog never reaches them.
That catalog gap is a known, repeatedly-handed-off finding (tools 41/43, Bean and
Tiffany cycles) — this tool is the first to score it as a funnel blocker rather
than an isolated note. The gateway's live $0.05 is the standing owner-gated price
ladder drift, unchanged; pricing is not touched here.

Honest external earned = **$0.00**. No payment-path incident: the 117 failed
challenges / 2909 in 24h are bot/scanner noise with no funded genuine payer.

## Handoffs (not executed — owner / other lanes)

- `@staci/@kip`: add `contract-eye-x402.fly.dev` and `raen-mcp-gateway.fly.dev` to
  `rae-fleet-router /catalog.json` to unblock `DISCOVER` (router/deploy lane).
- `@staci/@kip`: port breadth-crawler exclusion into collector `/stats` so the
  `REPEAT` stage can be read straight from the dashboard (`total_crawler_usdc` is
  still 0 while `$0.012` books as external).
- `@owner`: gateway $0.05 vs approved $0.005 ladder — standing owner-gated decision.

## Usage

```
python scripts/acquisition-funnel.py
python scripts/acquisition-funnel.py --out registry/acquisition-funnel.json
```

Snapshot: `registry/acquisition-funnel.json`; buyer card: `registry/acquisition-funnel.md`.
See also recipes 41 (trust coverage), 43 (buyer readiness), 47 (crawlable origin),
48 (schema parity), 50 (demand signal), 51 (breadth detector), 52 (chain reconciler).
