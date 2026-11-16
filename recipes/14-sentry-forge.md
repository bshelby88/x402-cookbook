---
permalink: /recipes/14-sentry-forge.md
---

# Recipe 14 — sentry-forge: one collection notice → 8 dispute docs

Turn one third-party debt-collection notice into eight review-ready validation and complaint documents. No subscription.

**Endpoint:** `POST https://sentry-forge-x402.fly.dev/api/dispute-pack` · **Price:** $5.00 USDC on Base (`eip155:8453`, scheme `exact`) · **Challenge below decoded live from this endpoint: 2026-11-15**

## 1. Decode the 402 challenge (the 60-second test)

```bash
curl -s -D headers.txt -o body.json -X POST \
  https://sentry-forge-x402.fly.dev/api/dispute-pack \
  -H 'Content-Type: application/json' \
  -d '{"customer_name": "Sample Consumer", "state": "LA", "contract_type": "credit_card", "default_date": "2026-06-10", "alleged_balance": 1842.17, "narrative": "I do not recognize this account and want the collector to provide enough information to identify it.", "collector_letter": "Example Collections LLC claims $1,842.17 on an account I do not recognize."}'
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
    "amount": "5000000",
    "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "payTo": "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f",
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
curl -s -X POST https://sentry-forge-x402.fly.dev/api/dispute-pack \
  -H 'Content-Type: application/json' \
  -d '{...}' \
  -H "PAYMENT-SIGNATURE: $ENVELOPE"
```

**HTTP 200** returns an 8-file review-ready validation and complaint pack as JSON (collector letter, CFPB drafts, bureau outlines, checklists) in markdown.

## 3. Already settled but got no payload?

An EIP-3009 nonce is **at-most-once** — if you paid on-chain but the call failed
(crash, timeout, or an `already_settled` reply), the funds are not lost. The
fleet runs a claims desk: check **<https://settlement-collector.fly.dev/storefront/claims>** with your tx hash (live, verified
2026-11-15) and finish recovery at `/storefront/register` with your claim code
(format `RAEN-XXXXXXXXXX`).


Note: a bare **GET** on this route returns only a machine-readable quote body —
you must **POST** the customer JSON to receive the real 402 challenge.

Next: [Recipe 15 — dispute-forge](15-dispute-forge.md)
