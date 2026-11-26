# Recipe 35 — llms.txt buyer-surface linter (does your discovery doc tell the truth?)

**Status:** shipped 2026-11-26 (Tiffany, machine-buyer acquisition). Free, read-only,
unpaid-HTTP-only, stdlib-only. No signing, no `X-PAYMENT`, no RPC money calls,
no funds movement, no POST to any directory, no external sends.

A machine buyer does not open your API first. It reads `llms.txt` — the
machine-discovery card — and decides there whether you are worth a call. If that
card names the wrong payTo, omits it entirely, or quotes a stale price, the
buyer either misroutes funds or leaves before your live 402 ever gets to tell
the truth. Docs are a buyer surface; drift there is lost acquisition, not a
cosmetic bug.

This tool checks every live RAEN `llms.txt` against two independent truths:

1. the **canonical address set** (canonical / retired / internal AgentCash), and
2. a **fresh live 402 challenge** (`accepts[0].amount`, `payTo`, `network`) from
   the paid route itself.

The live 402 is authoritative. Where a doc disagrees, the doc is wrong.

## Run it

```bash
python3 scripts/llms-lint.py
python3 scripts/llms-lint.py --json --out registry/llms-lint.json
```

`--json` emits the full report: per-surface address roles and prices, the live
402 decode per probed route, a `findings` list and a `verdict`.

Exit codes: `0` CLEAN, `1` DRIFT (a payment-context address is not canonical —
CI hard-block), `2` all surfaces unreachable. A GAP (missing `llms.txt`, missing
canonical payTo, stale doc price) is reported but is **an acquisition
opportunity, not a failure** — fixing it is a source/deploy action in the
owner/kip lane under the current freeze.

## Truth rules baked in

- Full 42-character, case-insensitive address compare — never a shorthand like
  `0xfbc0…2240` (a known homoglyph already produced a false census).
- `0xfbc0eb7811d477e55261d956df39f0046e192240` is the **internal AgentCash test
  wallet**. Presenting it as a "Payer wallet" to a buyer is DRIFT: a buyer could
  pay the wrong address.
- The retired payee `0x7861…f1393` is legitimate in a labelled *stranding watch*
  line, but DRIFT in a payment-instruction line. Watch/tracking lines are
  excluded from the payment-context scan (fixed after a first run produced
  exactly that false positive — corrected, not hidden).
- Price compare uses the x402 **v2** `amount` field (micro-USDC), divided by
  1e6 — never `maxAmountRequired`, never a hand-maintained price table.

## Live result — 2026-11-26 (6/6 surfaces up, verdict DRIFT)

| Finding | Surface | Evidence |
|---|---|---|
| DRIFT `NONCANONICAL_PAYMENT_ADDRESS` | gateway | "Payer wallet: `0xfbc0…92240`" = internal AgentCash, not canonical |
| GAP `MISSING_CANONICAL_PAYTO` | router, contract-eye, nanobanana, sentry-forge, gateway | no canonical address in the buyer doc |
| GAP `STALE_DOC_PRICE` | contract-eye | doc `$0.05`, live 402 `amount=5000` = **$0.005** |
| GAP `STALE_DOC_PRICE` | royal-ruby | doc `$0.25`, live 402 `amount=50000` = **$0.05** |

Live 402 decodes (authoritative): contract-eye `eip155:8453` / `5000` /
`0x9b8a27e0…f72f`; royal-ruby `eip155:8453` / `50000` / canonical; gateway
`/mcp` `eip155:8453` / `50000` / canonical. All three payTo values are canonical —
the drift is in the *docs*, not the walls.

## TIFF-PLAN-19 content pack — drop-in corrected blocks

Prepared, **not applied** (no deploy, no source push — BURN FREEZE). Source edit
is the owner/kip lane. Text below is ready to paste into each service's
`llms.txt` generator/template.

### Gateway — replace the Payments paragraph

```text
## Payments
x402 / USDC on Base (eip155:8453). First call free per wallet (charge-and-rebate, net $0).
PayTo: 0x9b8a27e03ceba490953cda8ab1291c0e13baf72f
Asset: USDC 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
Unpaid POST returns a live 402 challenge — the challenge is authoritative for price.
(Internal test payer 0xfbc0eb7811d477e55261d956df39f0046e192240 is NOT a payable destination.)
```

### Shared directory block (contract-eye / nanobanana / sentry-forge)

Two price lines are wrong; change only these:

```text
- contract-eye — https://contract-eye-x402.fly.dev — Contract risk-clause analysis (text or address) — $0.005 USDC/Base
- royal-ruby — https://royal-ruby-x402.fly.dev — Plain-language US consumer-protection law lookups — $0.05 USDC/Base
```

And append a verification block to each of those three docs:

```text
## Payment destination
All paid requests: x402 / USDC on Base (eip155:8453).
PayTo: 0x9b8a27e03ceba490953cda8ab1291c0e13baf72f
Asset: USDC 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
An unpaid POST to any paid route returns the authoritative live 402 challenge.
```

### Router — append a Payments section

```text
## Payments
x402 / USDC on Base (eip155:8453), pay-per-call, no API key.
PayTo: 0x9b8a27e03ceba490953cda8ab1291c0e13baf72f
Asset: USDC 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
Sign transferWithAuthorization; re-send with X-PAYMENT. Live 402 is authoritative.
```

Re-run `python3 scripts/llms-lint.py --json` after any applied change; the
DRIFT/GAP counts must drop and the snapshot must be regenerated.

## Why this is acquisition, not housekeeping

The machine buyer's first three questions are: *is it listed, what does it cost,
where do I pay?* `llms.txt` answers all three before any code runs. A wrong
destination address can strand funds; a stale price makes a $0.005 wall look
like $0.05 and loses the call. This linter keeps the first surface an agent reads
honest, and produces a ready-to-apply correction pack instead of just a complaint.

Companion recipes: 23 (live 402 preflight), 24 (fleet price oracle), 27 (receipt
proof), 31 (catalog parity), 32 (failure triage), 33 (address guard), 34 (broker
presence). Recipe 35 is the **discovery-doc** layer that precedes all of them.
