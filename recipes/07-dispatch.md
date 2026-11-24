---
permalink: /recipes/07-dispatch.md
---

# Recipe 07 — dispatch: route any intent to the right fleet service

One endpoint that picks the right paid fleet service for a natural-language intent and hands you a ready-to-use request.

**Endpoint:** `POST https://dispatch-x402.fly.dev/dispatch` · **Price:** **$0.01** USDC on Base (`eip155:8453`, scheme `exact`) — owner-approved 2026-11-24 ladder price; repriced deploy rolling out — until it lands, your live 402 challenge shows the pre-ladder $0.50 and is authoritative. Bulk 10+ @ $0.005 · $0.001 probe. · **Challenge below decoded live from this endpoint: 2026-11-15**

## 1. Decode the 402 challenge (the 60-second test)

```bash
curl -s -D headers.txt -o body.json -X POST \
  https://dispatch-x402.fly.dev/dispatch \
  -H 'Content-Type: application/json' \
  -d '{"intent": "create an escrow between two agents", "params": {}}'
```

You get **HTTP 402 Payment Required**. The challenge rides in the
`payment-required` response header (base64 JSON) and is mirrored in the body.
Decode it:

```bash
python - <<'EOF'
import base64, json
val = open("headers.txt").read().split("payment-required:", 1)[1].splitlines()[0].strip()
val += "=" * (-len(val) % 4)          # tolerate stripped padding
print(json.dumps(json.loads(base64.b64decode(val)), indent=2))
EOF
```

A live challenge from this exact endpoint (captured 2026-11-15) — **pay exactly
what your challenge says**; amounts are atomic USDC units (6 decimals):

```json
[
  {
    "scheme": "exact",
    "network": "eip155:8453",
    "amount": "500000",
    "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "payTo": "0x9b8a27e03CEbA490953cDa8AB1291c0E13bAf72f",
    "maxTimeoutSeconds": 300,
    "extra": {
      "name": "USD Coin",
      "version": "2",
      "facilitator": "https://raen-facilitator.fly.dev/facilitator"
    }
  }
]
```

## 2. Settle and retry

1. **Settle:** pay `amount` of USDC to `payTo` on Base and sign an EIP-3009
   `transferWithAuthorization` envelope built from this challenge — bring your
   own signer or use the [x402 SDK](https://github.com/coinbase/x402). Full
   client walkthrough: [Recipe 02](02-python-client.md).
2. **Retry the identical POST** with the envelope:

```bash
curl -s -X POST https://dispatch-x402.fly.dev/dispatch \
  -H 'Content-Type: application/json' \
  -d '{...}' \
  -H "PAYMENT-SIGNATURE: $ENVELOPE"
```

**HTTP 200** returns {"ok": true, "tier": "auto", "confidence": 0.93, "route": {...}, "call": {"method": "POST", "url": "https://escrow-x402.fly.dev/api/escrow/create", "price": "$0.005 (ladder, rolling out — was $0.05)"}}}.

## 3. Already settled but got no payload?

An EIP-3009 nonce is **at-most-once** — if you paid on-chain but the call failed
(crash, timeout, or an `already_settled` reply), the funds are not lost. The
fleet runs a claims desk: check **<https://settlement-collector.fly.dev/storefront/claims>** with your tx hash (live, verified
2026-11-15) and finish recovery at `/storefront/register` with your claim code
(format `RAEN-XXXXXXXXXX`).


The `call` object in the response **is** the downstream request — take its
`url`, `method` and price straight into that service's recipe (e.g.
[Recipe 13 — escrow](13-escrow.md)). See also [Recipe 05](05-dispatch-router.md)
for the free `/classify` preview.

Next: [Recipe 08 — contract-eye](08-contract-eye.md)
