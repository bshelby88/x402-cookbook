# 44. Machine-Buyer Client Bootstrap — from live 402 to runnable client code

*Tiffany Innovation 44 · 2026-11-26 · read-only, stdlib-only, no funds moved*

## The problem

A machine buyer can now discover RAEN (intent matcher, broker monitor), pick a
wall (paywall picker, readiness scorecard), verify the price (price oracle), get
a trustworthy challenge (conformance doctor), and prove a payment landed
(receipt verifier). What none of the 43 tools does is hand the agent the **last
mile**: runnable client code that turns a live 402 into a signed retry.

Every integration guide is prose that a buyer must re-derive. An autonomous
agent wants a skeleton it can paste, with the real price / payTo / network
already filled in from the wall itself — and with a hard stop before any payment.

## What this tool does

`scripts/client-bootstrap.py` probes each kept-live paid wall with an **unpaid
POST**, decodes the x402 v2 `payment-required` header, and emits:

- `registry/client-bootstrap.json` — a live snapshot of each wall's endpoint,
  method, request body, price (`amount` / 1e6), `asset`, `scheme`, `network`,
  full `payTo`, and a per-field canonical check.
- `registry/client-bootstrap.md` — a buyer-facing table plus a **run-ready Python
  skeleton** (stdlib only) with the live-derived values injected.

The 4-step flow the buyer follows:

1. **Unpaid call** → receive the 402 `payment-required` header (base64 JSON).
2. **Decode** `accepts[0]`: `scheme`, `network`, `payTo`, `amount` (atomic USDC, 6 dp).
3. **Preflight assert** `payTo` equals the full canonical address (case-insensitive,
   homoglyph-safe), `scheme=exact`, `network=eip155:8453`, `amount>0`. Never pay a lookalike.
4. **Sign with YOUR wallet** (EIP-3009 `transferWithAuthorization` on Base) → base64
   `X-PAYMENT` → retry the call and read the deliverable.

## Honesty / safety rules baked in

- The tool **never signs, never sends an `X-PAYMENT` header, never makes an RPC
  money call, never moves funds, never touches a key**. The generated skeleton's
  `build_payment_header()` is a stub that raises `NotImplementedError` until the
  buyer plugs in their own signer.
- The **live 402 is authoritative** — price and payTo come from the challenge, not
  a hand-maintained table.
- CI fails **only** on a canonical break (non-canonical payTo, wrong scheme/network,
  non-positive amount, or an undecodable challenge). WARNs never fail CI.
- BURN FREEZE respected: only kept-live walls are probed; frozen services are never
  touched locally.

## Run it

```
python3 scripts/client-bootstrap.py
python3 scripts/client-bootstrap.py --out-json registry/client-bootstrap.json \
    --out-md registry/client-bootstrap.md
```

Exit codes: `0` all probed walls canonical · `1` a canonical break · `2` no wall reachable.

## Live result — 2026-11-26T14:42Z

Verdict `OK`, 4/4 walls canonical, 0 breaks:

| Wall | Endpoint | Live price | Scheme / network | Canonical payTo |
|---|---|---|---|---|
| royal-ruby | `POST /api/law-lookup` | $0.0050 | `exact` / `eip155:8453` | yes |
| contract-eye | `POST /api/analyze-contract` | $0.0050 | `exact` / `eip155:8453` | yes |
| nanobanana | `POST /api/generate-image` | $0.0100 | `exact` / `eip155:8453` | yes |
| raen-mcp-gateway | `POST /mcp` | $0.0500 | `exact` / `eip155:8453` | yes |

Snapshots: `registry/client-bootstrap.json` (machine-readable) and
`registry/client-bootstrap.md` (buyer copy with the runnable skeleton).

## Buyer takeaway

Copy the skeleton, select a wall by name, and plug in your own x402 signer. The
preflight assertion refuses to pay any wall whose `payTo` is not the full canonical
`0x9b8a27e03ceba490953cda8ab1291c0e13baf72f`. This turns "how do I actually pay
this?" from a doc-reading exercise into a paste-and-sign step — the last mile of
machine-buyer acquisition.
