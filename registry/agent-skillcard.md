---
name: raen-x402-buyer
description: >-
  Buy paid AI services from the RAEN x402 fleet on Base. Use when an autonomous agent needs to call a RAEN paid endpoint: live-verified prices, canonical payTo guard, EIP-3009 checkout order and claims-desk fallback in one portable file.
---

# RAEN x402 buyer card (installable)

Copy this file into your agent's `skills/` directory or paste it into your system instructions. It is self-contained and read-only.

**Snapshot generated** `2026-11-26T15:50:55Z` (UTC). Every price and payTo below was read live from an unpaid 402 challenge at that time. The **live 402 is authoritative** — re-read it at purchase time; a snapshot is never a contract.

## Hard rules

1. Only pay a `payTo` equal to the FULL 42-character canonical address `0x9b8a27e03ceba490953cda8ab1291c0e13baf72f` (case-insensitive). Reject prefixes, suffixes, lookalikes, and the retired `0x7861db4efc14a1ed5dd8c96c528a3796560f1393`.
2. Verify the decoded challenge: `x402Version==2`, `scheme=='exact'`, `network=='eip155:8453'`, integer `amount > 0`, asset is USDC on Base.
3. Sign EIP-3009 `transferWithAuthorization` with YOUR OWN wallet for the exact terms in the challenge. Never reuse a signature, never pay a different amount or address.
4. Do not treat a 402 as an error or as a completed purchase. A 402 is the seller's price quote; a 2xx after the signed retry is the deliverable.
5. If a settled payment yields no deliverable, use the claims desk at `https://royal-ruby-x402.fly.dev/` (`?payer=<your-address>`) instead of paying twice. Public telemetry: `https://settlement-collector.fly.dev/stats`.
6. Never put keys, wallet secrets or signed headers in chat, logs, issues or this card.

## Live walls (verdict: OK at snapshot time)

| Service | Endpoint | Offer | Price | Unpaid request body |
| --- | --- | --- | --- | --- |
| `royal-ruby` | `https://royal-ruby-x402.fly.dev/api/law-lookup` | Statutory law lookup with cited baseline | $0.005 | `{"query":"x402 skillcard probe"}` |
| `contract-eye` | `https://contract-eye-x402.fly.dev/api/analyze-contract` | Contract risk analysis | $0.005 | `{"text":"x402 skillcard probe"}` |
| `nanobanana` | `https://nanobanana-x402.fly.dev/api/generate-image` | Image generation | $0.01 | `{"prompt":"x402 skillcard probe"}` |
| `raen-mcp-gateway` | `https://raen-mcp-gateway.fly.dev/mcp` | MCP tool call gateway (tools/list is free for discovery) | $0.05 | `{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"raen_law_lookup","argum...` |

## Checkout order (one call)

1. `POST` the request body from the table to the wall's URL with `Content-Type: application/json` and **no** payment header.
2. Expect `402`. Base64-decode the `payment-required` header into the x402 v2 envelope; read `accepts[0]`.
3. Apply the Hard rules guards. If any fails, STOP — do not sign.
4. Sign the exact `accepts[0]` terms with your wallet (EIP-3009 on Base) and retry the same request with the base64 `X-PAYMENT` header.
5. Read the 2xx deliverable. Verify it is the advertised output, not a `degraded` placeholder.

Free discovery before paying: `tools/list` on the MCP gateway is open; `/.well-known/x402.json` on each wall advertises its schema. Cross-check docs against the live 402 — when they disagree, the live 402 wins.

## Honesty

RAEN publishes real telemetry, including $0 external revenue. This card asserts a price snapshot and a payTo guard only; it does not promise uptime, output quality or a refund outside the claims desk.
