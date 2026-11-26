---
permalink: /recipes/40-dev-education.md
---

# Recipe 40 — x402 for Developers: a live-grounded three-part course

**Status:** shipped 2026-11-26 (Tiffany, machine-buyer acquisition, Airtable POST-102). Free, read-only, unpaid-HTTP-only, stdlib-only. No signing, no `X-PAYMENT`, no RPC money calls, no funds movement, no external sends, no directory POSTs, no deploys. BURN FREEZE: only kept-live walls are probed.

POST-102 asked for a three-part "x402 for Developers" educational series in a markdown file, each article with code examples. The risk in developer education is drift: a hand-typed price or address teaches the buyer to pay the wrong amount or the wrong (lookalike) wallet. Recipe 40 generates the entire course from LIVE surfaces — every price, payTo, network and request shape is read from a fresh unpaid 402 and the seller's own manifest.

The script: [`scripts/dev-education.py`](../scripts/dev-education.py). Outputs: `registry/dev-education.json` (machine-readable truth snapshot) and `x402_developer_education.md` (the 3-article course; POST-102 acceptance artifact).

## What it does

For each kept-live wall (royal-ruby `/api/law-lookup`, contract-eye `/api/analyze-contract`, gateway `/mcp` tools/call):

1. Reads `/.well-known/x402.json` for the seller's published request fields, and `/openapi.json` for documentation status.
2. Sends one unpaid POST and decodes the base64 `payment-required` header — `accepts[0]` gives `amount` (atomic USDC), `payTo`, `network`, `scheme`. This is the only price truth.
3. Emits three complete articles:
   - **Article 1 — Introduction:** what `402` carries, the four fields in a challenge, free discovery vs the paid wall, and a first no-signing probe.
   - **Article 2 — Integration:** read the published request shape, decode and pin the truth, sign EIP-3009 with the buyer's own wallet, retry with `X-PAYMENT` (not the stale `PAYMENT-SIGNATURE`), verify the receipt on-chain.
   - **Article 3 — Advanced:** three-surface cross-check, full-42-char address guards, idempotency/failure triage, zero-value tiers (charge-and-rebate), telemetry priceMap derived from the challenge, and chain-scoped zero claims.
4. Enforces canonical payTo (full 42 chars, case-insensitive / homoglyph-safe), `eip155:8453`, `scheme=exact`; exit 1 on drift, 2 if no wall is reachable.

## Verified 2026-11-26

Verdict **CLEAN** — 3/3 kept-live walls returned a live 402 with full canonical payTo, `eip155:8453`, `exact`, 0 price drift: royal-ruby `/api/law-lookup` $0.05, contract-eye `/api/analyze-contract` $0.005, gateway `/mcp` tools/call $0.05. Gateway `tools/list` is correctly labelled FREE discovery. `py_compile` OK; the generated file contains 3 complete articles and 8 fenced code blocks. No real key, nothing signed.

## Honesty

A 402 is a demand signal, not a sale — most challenges are scanners. Internal AgentCash self-pays are not external revenue; fleet external revenue is $0.00 unless the chain says otherwise. Course examples are illustrative and sign nothing. Read-only, no deploy, no publishing.
