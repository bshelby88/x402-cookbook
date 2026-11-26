# 42 — x402 Challenge Conformance Doctor

*TIFFANY Innovation 42 · 2026-11-26 · read-only, stdlib-only, no account, no key, no payment.*

A machine buyer's x402 client cannot pay a wall unless the 402 is a **well-formed
challenge on the method the client actually calls**. Most buyer tooling checks the
price or the address. This one checks something earlier and more basic: **is the
challenge itself decodable, spec-shaped, and consistent with the seller's own
manifest on every HTTP method a client might use?**

The failure it catches is the `INVALID_CHALLENGE` trap: a GET/HEAD probe returns
`402 Payment Required` but with **no `payment-required` header** (only a friendly
JSON quote in the body). Third-party graders (x402 Doctor, CDP Bazaar) see a 402
with no `accepts[]` and grade the wall `no_go` — so the buyer walks away before a
single cent moves, even though the POST path is perfectly canonical. That is a
lost sale with no money, no logs, and no error the seller ever sees.

## Run it

```bash
cd x402-cookbook
python3 scripts/challenge-conformance.py > registry/challenge-conformance.json
# exit 0 = all manifest-advertised paid methods canonical; exit 1 = drift/break
```

No `pip install`, no `.env`, no wallet, no signing. It issues **unpaid** GET/HEAD/POST
probes and decodes the public challenge header. It never sends `X-PAYMENT`, never
calls an RPC money method, never moves funds, never posts anywhere.

## What it grades (per method)

| Check | Pass condition |
|---|---|
| `http_402` | paid route answers 402 |
| `decodable_challenge` | `payment-required` header is base64(JSON) |
| `x402_v2` | `x402Version == 2` |
| `accepts_nonempty` | `accepts[]` has at least one option |
| scheme / network | `exact` / `eip155:8453` |
| `payTo` | full 42-char canonical address, case-insensitive (homoglyph-safe) |
| `amount` | positive integer, USDC atomic units (÷ 1,000,000 = USD) |
| `resource.url` | matches the probed URL |
| `manifest_price_parity` | live `amount` == manifest `price` |
| free discovery | gateway `tools/list` stays 200 (discovery must not be gated) |

Verdicts: `CANONICAL`, `DRIFT`, `INVALID_CHALLENGE`, `UNREACHABLE`,
`NOT_APPLICABLE`. CI fails only on a break/DRIFT on a **manifest-advertised**
method. Extra-method problems are `WARN`: real buyer friction, not a paid-path break.

## Live result — 2026-11-26T12:20Z

Four kept-live paid walls, 12 method probes: **10 `CANONICAL`, 0 `DRIFT`,
2 `INVALID_CHALLENGE`, 0 `UNREACHABLE`**. `ci_verdict: PASS` — every advertised
POST method is canonical and price-correct.

| Wall | POST (advertised) | GET | HEAD | Live price | Manifest parity |
|---|---|---|---|---|---|
| royal-ruby `/api/law-lookup` | CANONICAL | **INVALID_CHALLENGE** | **INVALID_CHALLENGE** | $0.05 | no price in manifest |
| contract-eye `/api/analyze-contract` | CANONICAL | CANONICAL | CANONICAL | $0.005 | match |
| nanobanana `/api/generate-image` | CANONICAL | CANONICAL | CANONICAL | $0.01 | match |
| raen-mcp-gateway `/mcp` (tools/call) | CANONICAL | CANONICAL | CANONICAL | $0.05 | match |

All twelve canonical challenges carry the full canonical `payTo`
(`0x9b8a27e03ceba490953cda8ab1291c0e13baf72f`, case-insensitive), `exact`,
`eip155:8453`, `x402Version: 2`, and **`amount`** (not the legacy
`maxAmountRequired`). Gateway `tools/list` correctly stays 200 (free discovery).

### Honest findings (not hidden)

1. **royal-ruby GET + HEAD return 402 with no `payment-required` header.** The POST
   path is canonical ($0.05), but a generic client that reads the resource with
   GET/HEAD sees an undecodable challenge — the exact QUOTE-FIX v2 defect family
   already repaired on contract-eye, nanobanana and sentry-forge. Buyer impact:
   third-party graders can mark this wall `no_go` on a read probe. Hand-off:
   BEAN / CROWN. No fix attempted in this run (content lane, no deploys).
2. **royal-ruby's manifest `accepts` block omits `price`** (only scheme / network /
   payTo / maxTimeoutSeconds). Live 402 is authoritative at $0.05. Buyers must read
   the challenge, not the manifest, for the price on this wall.

## Why this matters for machine-buyer acquisition

Discovery, price lookup, preflight, checkout and receipts already have recipes
(24, 26, 23, 21, 27). None of them ask the question a generic agent asks first:
*"can I even parse this wall's challenge on the method I'm about to call?"*
A wall that fails here is invisible to the buyer's client — no payment, no
receipt, no dispute, just silence. This tool publishes the answer **before** the
buyer spends, and gives BEAN/CROWN a precise, reproducibly-located defect to fix.

Truth layers: coordination = Library, money = chain, code = GitHub,
runtime = these live probes. No claim here rests on a hand-maintained price table.

Snapshot: `registry/challenge-conformance.json` (generated_at stamped).
