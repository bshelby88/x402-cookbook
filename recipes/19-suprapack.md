---
permalink: /recipes/19-suprapack.md
---

# Recipe 19 — suprapack: search 531 curated agent skills

Search curated Claude Code / Hermes skills by keyword and get the full markdown of the best matches.

**Endpoint:** `POST https://suprapack-x402.fly.dev/api/find-skill` · **Price:** $0.03 USDC on Base (`eip155:8453`, scheme `exact`) · **Challenge below decoded live from this endpoint: 2026-11-15**

## 1. Decode the 402 challenge (the 60-second test)

```bash
curl -s -D headers.txt -o body.json -X POST \
  https://suprapack-x402.fly.dev/api/find-skill \
  -H 'Content-Type: application/json' \
  -d '{"query": "stripe webhook"}'
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
    "amount": "30000",
    "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "payTo": "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f",
    "maxTimeoutSeconds": 300,
    "extra": {
      "name": "USD Coin",
      "version": "2",
      "facilitator": "https://x402-agent-pay.com/facilitator"
    }
  }
]
```

> **TRUTH WARNING (decoded live 2026-11-22):** this service's live challenge
> advertises `https://x402-agent-pay.com/facilitator`, a known third-party
> dead-end that settles only to its own treasury (`PAYEE_NOT_SERVED_HERE` for
> every fleet payTo). Override the facilitator client-side to
> `https://raen-facilitator.fly.dev/facilitator` when paying this SKU; the
> example above is kept faithful to the live (broken) challenge. Service-side
> fix is owner-gated (redeploy).

## 2. Settle and retry

1. **Settle:** pay `amount` of USDC to `payTo` on Base and sign an EIP-3009
   `transferWithAuthorization` envelope built from this challenge — bring your
   own signer or use the [x402 SDK](https://github.com/coinbase/x402). Full
   client walkthrough: [Recipe 02](02-python-client.md).
2. **Retry the identical POST** with the envelope:

```bash
curl -s -X POST https://suprapack-x402.fly.dev/api/find-skill \
  -H 'Content-Type: application/json' \
  -d '{...}' \
  -H "PAYMENT-SIGNATURE: $ENVELOPE"
```

**HTTP 200** returns {"ok": true, "count": 2, "results": [{"slug": "stripe-integration", "quality": 9, "content": "# Stripe Integration\n...full markdown..."}]}.

## 3. Already settled but got no payload?

An EIP-3009 nonce is **at-most-once** — if you paid on-chain but the call failed
(crash, timeout, or an `already_settled` reply), the funds are not lost. The
fleet runs a claims desk: check **<https://settlement-collector.fly.dev/storefront/claims>** with your tx hash (live, verified
2026-11-15) and finish recovery at `/storefront/register` with your claim code
(format `RAEN-XXXXXXXXXX`).


Already know the slug? `POST /api/get-skill` with `{"slug": "..."}` fetches one
skill's full markdown — same $0.03 price.

Back to the [recipe index](https://bshelby88.github.io/x402-cookbook/).
