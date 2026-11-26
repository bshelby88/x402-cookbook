---
permalink: /recipes/39-developer-docs.md
---

# Recipe 39 — Pay with USDC: a live-grounded developer documentation pack

**Status:** shipped 2026-11-26 (Tiffany, machine-buyer acquisition, TIFF-PLAN-95). Free, read-only, unpaid-HTTP-only, stdlib-only. No signing, no `X-PAYMENT`, no RPC money calls, no funds movement, no external sends, no deploys. BURN FREEZE: only kept-live walls are probed.

A machine buyer's first integration question is "how do I actually pay and retry?" — and the answer must not come from a hand-maintained doc that drifts from the live wall. Recipe 39 turns the live surfaces into a **developer documentation pack**: a quickstart, an API reference table and three copy-paste integration examples, every price / payTo / network / request-shape claim read from a fresh unpaid 402 and the seller's own manifest.

The script: [`scripts/developer-docs.py`](../scripts/developer-docs.py). Outputs: [`registry/developer-docs.json`](../registry/developer-docs.json) and [`registry/developer-docs.md`](../registry/developer-docs.md).

## What it does

For each kept-live wall (royal-ruby `/api/law-lookup`, contract-eye `/api/analyze-contract`, gateway `/mcp` tools/call):

1. **Manifest** (`/.well-known/x402.json`): reads the seller's published request body (field names + example) and advertised price.
2. **Live 402** (unpaid POST): decodes `accepts[0]` — `amount` (atomic USDC), `payTo`, `network`, `scheme`. This is the only price truth.
3. **OpenAPI** (`/openapi.json`): records whether the route is documented.
4. Emits a quickstart (discover -> challenge -> sign EIP-3009 -> retry with `X-PAYMENT`), a live price/payTo reference table, and **three code examples**: (1) decode a live 402 with curl + Python stdlib, (2) attach `X-PAYMENT` and retry after signing with the buyer's own wallet, (3) three-surface cross-check before wiring a wall.
5. Enforces canonical payTo (full 42-char, case-insensitive), `eip155:8453`, `scheme=exact`; exit 1 on drift, 2 if no wall is reachable.

## Verified 2026-11-26

Verdict **CLEAN** — 3/3 kept-live walls returned a live 402 with the full canonical payTo, `eip155:8453`, `exact`, 0 price drift: royal-ruby `/api/law-lookup` $0.05, contract-eye `/api/analyze-contract` $0.005, gateway `/mcp` tools/call $0.05. Gateway `tools/list` is correctly labelled as FREE discovery, not a paid wall. Request fields are the sellers' published examples (the 402 precedes body validation, so a wrong-body probe cannot reveal a 400 unpaid). Examples contain no real key and sign nothing.

## Honesty

A 402 is a demand signal, not a sale — most challenges are scanners. Internal AgentCash self-pays are not external revenue; fleet external revenue is $0.00 unless the chain says otherwise. This pack verifies Base only. Frozen services are never probed. Read-only, no deploy, no publishing.
