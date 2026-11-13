# Recipe 03 — Free first call: charge-and-rebate on royal-ruby

Your first call to royal-ruby can cost **net $0**. The mechanism is honest
charge-and-rebate: you pay the normal challenge, the service rebates the full amount
right after settlement. Both legs are on-chain.

> Why not a $0 challenge? x402 facilitators reject zero-value challenges, so a "free"
> call is implemented as **pay-then-rebate** instead.

## Step by step

1. **Check eligibility** — one rebate per wallet per 30 days. New wallet? You're set.
2. **Get the challenge:**

```bash
curl -s -D h.txt -o b.txt -X POST \
  https://royal-ruby-x402.fly.dev/api/law-lookup \
  -H 'Content-Type: application/json' -d '{}'
```

3. **Pay the challenge** (typically $0.05; a disclosed A/B price bucket sees $0.03 —
   whatever your challenge says is what you pay), and include your wallet so the
   rebate knows where to go:

```
PAYMENT-SIGNATURE: <EIP-3009 envelope>
x-payer-address: 0xYourWalletAddress
```

4. **Get your answer** (HTTP 200) — the service settles your payment and immediately
   rebates the full charged amount back to `x-payer-address`.

## Verify everything yourself

- Full walkthrough with live verification links:
  **[raen-first-call-free](https://bshelby88.github.io/raen-first-call-free/)**
- The offer is disclosed in the live manifest:
  <https://royal-ruby-x402.fly.dev/.well-known/x402.json> (`firstCallFree: true`,
  offer type `charge-and-rebate`).
- Rebates are keyed on **settled** payments — if the settle fails, nothing rebates.

## Honesty notes

- The rebate is the actual charged amount (the price-experiment amount, not a
  hardcoded $0.05).
- When the LLM enhancer is unavailable, royal-ruby still answers with a deterministic
  statutory baseline (`mode: statutory-baseline`) with verified citations — the
  manifest says so up front.

Next: [Recipe 04 — MCP gateway](04-mcp-gateway.md).
