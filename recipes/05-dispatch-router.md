---
permalink: /recipes/05-dispatch-router.md
---

# Recipe 05 — dispatch: route intents without a services map

One endpoint that reads an agent's natural-language intent and returns the right paid
fleet service, with extracted params and ready-to-use call instructions.

## Free preview: /classify

```bash
curl -s -X POST https://dispatch-x402.fly.dev/classify \
  -H 'Content-Type: application/json' \
  -d '{"intent":"check NFT floor price"}'
```

Live example response (abridged):

```json
{
  "ok": true,
  "tier": "ambiguous",
  "confidence": 0.5,
  "route": {
    "id": "nft-alpha",
    "name": "NFT Alpha — OpenSea market signals",
    "base": "https://nft-alpha-x402.fly.dev",
    "endpoint": "/api/nft-signal",
    "price": "$0.10"
  },
  "suggested_params": { }
}
```

`/classify` is free — use it to budget a task before spending anything.

## Paid: /dispatch ($0.50)

The priced primitive is the routing decision itself: the paid call returns the
authoritative route, extracted parameters, and exact call instructions for the target
service.

```bash
# 1) get the 402 challenge (also mirrored in the body)
curl -s -X POST https://dispatch-x402.fly.dev/dispatch \
  -H 'Content-Type: application/json' \
  -d '{"intent":"draft a dispute letter for a late-payment entry"}'

# 2) settle the $0.50 USDC challenge (see Recipe 02), then retry with payment:
curl -s -X POST https://dispatch-x402.fly.dev/dispatch \
  -H 'Content-Type: application/json' \
  -H 'PAYMENT-SIGNATURE: <EIP-3009 envelope>' \
  -d '{"intent":"draft a dispute letter for a late-payment entry"}'
```

A bare **GET** on `/dispatch` returns a machine-readable 402 quote if you just want
the price.

## Why route through dispatch?

- No services map to maintain — new fleet services appear in routing automatically.
- Cost planning: classify (free) → know the target price → pay once for the exact
  call recipe.
- The full agent-directory with per-endpoint prices and copy-paste clients for 14
  frameworks: <https://bshelby88.github.io/raen-agent-directory/>

Back to the [README](../README.md).
