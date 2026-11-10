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
| [dispute-forge](https://dispute-forge-x402.fly.dev/.well-known/x402.json) | FCRA-compliant dispute letter + on-chain certificate | $0.75 |
| [vault-pro](https://vault-pro-x402.fly.dev/.well-known/x402.json) | Obsidian project/agent scaffolding markdown | see manifest |
| [sentry-forge](https://sentry-forge-x402.fly.dev/.well-known/x402.json) | One collection notice → 8 review-ready dispute docs | $5.00 |
| [settlement-collector](https://settlement-collector.fly.dev/stats) | Fleet telemetry (free, public JSON) | free |

Prices marked "see manifest" come from the live manifest — always confirm against it; it is the source of truth.

## Recipes

1. **[curl — decode your first 402 challenge](recipes/01-curl-402-decode.md)** — understand the protocol in 60 seconds.
2. **[Python — generic paid-call client](recipes/02-python-client.md)** — a ~40-line client that fetches the challenge, signs, retries, works for any fleet service. *(Bring your own EIP-3005 signer or use the [x402 SDK](https://github.com/coinbase/x402).)*
3. **[Free first call — charge-and-rebate](recipes/03-free-first-call.md)** — try royal-ruby for net $0 with one extra header. Step-by-step walkthrough with verify-everything links: **[raen-first-call-free](https://bshelby88.github.io/raen-first-call-free/)**.
4. **[MCP — use the fleet from any MCP client](recipes/04-mcp-gateway.md)** — Bearer-gated gateway at `raen-mcp-gateway.fly.dev/mcp`.
5. **[dispatch — route intents without a services map](recipes/05-dispatch-router.md)** — one endpoint that picks the right tool.

## MCP registry

RAEN's MCP gateway is listed at `io.github.bshelby88/raen-mcp` on the MCP Registry.

## Honesty

Fleet telemetry is public and unedited: <https://settlement-collector.fly.dev/stats>. We publish real numbers, including zero revenue.

MIT licensed. Not legal or financial advice.
