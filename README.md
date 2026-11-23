# x402 Integration Cookbook — RAEN Fleet

Copy-paste recipes for paying RAEN's 12 x402 services with USDC on Base mainnet from any agent (Python, Node, curl, MCP).

**Payee (all services):** `0x9b8a27e03ceba490953cda8ab1291c0e13baf72f`
**Network:** `eip155:8453` (Base) · **Scheme:** `exact` · **Asset:** USDC `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`

## The fleet

| Service | What it does | Price |
|---|---|---|
| [royal-ruby](https://royal-ruby-x402.fly.dev/.well-known/x402.json) | US consumer-rights law citation lookup (FCRA/FDCPA/TILA/UDAP). **Free first call** (charge-and-rebate — net $0) | $0.05 |
| [contract-eye](https://contract-eye-x402.fly.dev/.well-known/x402.json) | Contract risk analysis, flags one-sided clauses | $0.05 |
| [tradingagents](https://tradingagents-x402.fly.dev/.well-known/x402.json) | Synthetic degraded demo payload (currently in demo mode) | $0.05 |
| [nanobanana](https://nanobanana-x402.fly.dev/.well-known/x402.json) | Gemini image generation/editing, base64 PNG out | see manifest |
| [briefsnap](https://briefsnap-x402.fly.dev/.well-known/x402.json) | Document summarization + action items | see manifest |
| [nft-alpha](https://nft-alpha-x402.fly.dev/.well-known/x402.json) | OpenSea market signals for Base collections | see manifest |
| [dispatch](https://dispatch-x402.fly.dev/.well-known/x402.json) | NL intent router → picks the right paid fleet service | $0.50 |
| [escrow](https://escrow-x402.fly.dev/.well-known/x402.json) | Agent-to-agent USDC escrow on Base, 1% fee, timeout-refundable | see manifest |
| [dispute-forge](https://dispute-forge-x402.fly.dev/.well-known/x402.json) | FCRA-compliant dispute letter + on-chain certificate | $0.10 |
| [vault-pro](https://vault-pro-x402.fly.dev/.well-known/x402.json) | Obsidian project/agent scaffolding markdown | see manifest |
| [sentry-forge](https://sentry-forge-x402.fly.dev/.well-known/x402.json) | One collection notice → 8 review-ready dispute docs | $5.00 |
| [settlement-collector](https://settlement-collector.fly.dev/stats) | Fleet telemetry (free, public JSON) | free |

Prices marked "see manifest" come from the live manifest — always confirm against it; it is the source of truth.

## Paid but got nothing? The claims desk (read this before paying twice)

If you settled USDC and never received your payload, **do not pay again**. Look
up your payment by **tx hash or wallet address** — the lookup confirms your
claim code (`RAEN-<sha256(tx)[:10]>`, derivable from your own tx), its delivery
state, and the self-serve register-for-redelivery path:

```bash
curl -s "https://settlement-collector.fly.dev/storefront/claims?tx=<your-tx-hash>"
# or: ?payer=<your-address>   then register: POST /storefront/register {tx_or_intent, email | callback_url}
```

Full walkthrough: **[recipe 22 — the claims desk](recipes/22-claims-desk.md)**.
This includes payments to the retired payee `0x7861…1393`: that wallet is still
served AND watched (auto order + claim code per transfer — status at
`/storefront/legacy-watch`), so a legacy-named settle is never invisible.

## Machine-buyer trust: verify the payTo BEFORE you pay

**[registry/payto-registry.json](registry/payto-registry.json)** — machine-readable
trust registry. Every entry is confirmed by decoding a LIVE 402 challenge (not the
manifest). Fetch it, decode your challenge, compare `accepts[].payTo` to
`canonical_payto` **case-insensitively**. Reject the retired wallet
`0x7861db4efc14a1ed5dd8c96c528a3796560f1393` and homoglyph lookalikes —
malicious directories have carried them. Five-line verification recipe is inside the file.

## Claims desk for machine buyers — settled but got nothing? self-recover

**<https://settlement-collector.fly.dev/storefront/claims>** — the first claims desk we
know of for machine buyers. If you settle an x402 challenge and the payload never
arrives, don't write the money off and don't email a human:

- `GET /storefront/claims?tx=<your-tx-hash>` — lookup by settlement tx
- `GET /storefront/claims?address=<your-payer-address>` — lookup by payer wallet

Both return JSON: matched settlements, open claims, and the resolve URL. No login, no
email required. Machine registration: `POST /storefront/register {tx_or_intent, agent_id,
callback_url}` — receipt + claims delivered to your `callback_url` as an HTTP POST.

Verified live 2026-11-22 (tx-hash and address lookups both answer; register flow live).
The desk exists because of our own honest zero: the only external money the fleet ever
received ($0.05, 2026-11-11, settle-crawler) initially went unfulfilled — a buyer who
paid and got nothing. The desk now shows that claim (`RAEN-8922B9225B`) registered and
**delivered via webhook**: `GET /storefront/claims?tx=0xf61129a8…c77cf37e` returns the
full record. Every recipe below carries the same fallback link.

## Recipes

1. **[curl — decode your first 402 challenge](recipes/01-curl-402-decode.md)** — understand the protocol in 60 seconds.
2. **[Python — generic paid-call client](recipes/02-python-client.md)** — a ~40-line client that fetches the challenge, signs, retries, works for any fleet service. *(Bring your own EIP-3009 signer or use the [x402 SDK](https://github.com/coinbase/x402).)*
3. **[Free first call — charge-and-rebate](recipes/03-free-first-call.md)** — try royal-ruby for net $0 with one extra header. Step-by-step walkthrough with verify-everything links: **[raen-first-call-free](https://bshelby88.github.io/raen-first-call-free/)**.
4. **[MCP — use the fleet from any MCP client](recipes/04-mcp-gateway.md)** — Bearer-gated gateway at `raen-mcp-gateway.fly.dev/mcp`.
5. **[dispatch — route intents without a services map](recipes/05-dispatch-router.md)** — one endpoint that picks the right tool.

### Per-SKU buyer recipes — decode → settle → retry, verified against the live 402 challenge (Nov 15, 2026)

Each recipe is one SKU, copy-paste, 60-second testable: unpaid call → decode the
402 challenge (real captured values) → settle + retry → claim-code fallback if
you settled but got no payload.

6. **[royal-ruby — consumer-law citations](recipes/06-royal-ruby.md)** — $0.05, first call free (charge-and-rebate).
7. **[dispatch — route any intent](recipes/07-dispatch.md)** — $0.50, returns a ready-to-use downstream request.
8. **[contract-eye — flag one-sided clauses](recipes/08-contract-eye.md)** — $0.05.
9. **[briefsnap — summarize any document](recipes/09-briefsnap.md)** — $1.00.
10. **[nanobanana — image generation](recipes/10-nanobanana.md)** — $0.01, base64 PNG out.
11. **[nft-alpha — OpenSea signals on Base](recipes/11-nft-alpha.md)** — $0.02.
12. **[vault-pro — Obsidian project scaffolding](recipes/12-vault-pro.md)** — $0.05.
13. **[escrow — agent-to-agent USDC escrow](recipes/13-escrow.md)** — $0.05 create fee, 1% release fee.
14. **[sentry-forge — 8 dispute docs from one notice](recipes/14-sentry-forge.md)** — $5.00.
15. **[dispute-forge — dispute letter + on-chain certificate](recipes/15-dispute-forge.md)** — $0.10.
16. **[tradingagents — ticker consensus (demo)](recipes/16-tradingagents.md)** — $0.05, synthetic demo payload (disclosed).
17. **[x402-enterprise — dispute letter (enterprise variant, self-identifies as dispute-forge)](recipes/17-x402-enterprise.md)** — $0.75.
18. **[staci-tradingagents — full pipeline run](recipes/18-staci-tradingagents.md)** — $5.00, simulated engine (disclosed).
19. **[suprapack — search 531 curated agent skills](recipes/19-suprapack.md)** — $0.03.
20. **[royal-ruby ping — $0.001 alive-check](recipes/20-royal-ruby-ping.md)** — the cheapest settled liveness probe in the ecosystem: one GET, `{status:'alive', block, latency_ms, catalog_url}`. Machine registration by webhook: `POST /storefront/register {tx_or_intent, agent_id, callback_url}` — receipt + claims delivered as HTTP POST, no email.
21. **[Machine checkout without email](recipes/21-machine-checkout.md)** — the full prepaid-pack loop for machine buyers: pay → register with `callback_url` → delivery webhook with one-time `claim_code` → redeem at the live API via `X-RAEN-CREDIT`. No email ever.
22. **[The claims desk — paid but got nothing](recipes/22-claims-desk.md)** — look up your payment by tx hash or wallet address, recover your claim code (`RAEN-<sha256(tx)[:10]>`), register for re-delivery (email or webhook), verify/redeem prepaid credits. Includes the retired-payee stranding watch.

## MCP registry

RAEN's MCP gateway is listed at `io.github.bshelby88/raen-mcp` on the MCP Registry.

## Honesty

Fleet telemetry is public and unedited: <https://settlement-collector.fly.dev/stats>. We publish real numbers, including zero revenue.

MIT licensed. Not legal or financial advice.
6. **[x402 Payback Calculator](https://bshelby88.github.io/raen-payback-calculator/)** — see what pay-per-call actually costs vs a flat SaaS subscription at your call volume.
7. **[x402 Launch Readiness Scorecard](https://bshelby88.github.io/x402-scorecard/)** — shipping your own paid API? Score how agent-ready it is in 60 seconds.
