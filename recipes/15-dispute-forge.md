---
permalink: /recipes/15-dispute-forge.md
---

# Recipe 15 — dispute-forge: dispute letter + on-chain certificate

An FCRA-compliant dispute letter plus a unique SVG certificate of dispute, signed and timestamped.

**Endpoint:** `POST https://dispute-forge-x402.fly.dev/api/dispute-pack` · **Price:** $0.10 USDC on Base (`eip155:8453`, scheme `exact`) · **Challenge below decoded live from this endpoint: 2026-11-22**

## 1. Decode the 402 challenge (the 60-second test)

```bash
curl -s -D headers.txt -o body.json -X POST \
  https://dispute-forge-x402.fly.dev/api/dispute-pack \
  -H 'Content-Type: application/json' \
  -d '{"creditor": "Acme Collections LLC", "reason": "Debt is not mine / inaccurate reporting"}'
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

A live challenge from this exact endpoint (decoded from the wire 2026-11-22) — **pay exactly
what your challenge says**; amounts are atomic USDC units (6 decimals). The live
`amount` is `100000` = **$0.10**; if your decode shows anything else, trust your decode:

```json
[
  {
    "scheme": "exact",
    "network": "eip155:8453",
    "amount": "100000",
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
curl -s -X POST https://dispute-forge-x402.fly.dev/api/dispute-pack \
  -H 'Content-Type: application/json' \
  -d '{...}' \
  -H "PAYMENT-SIGNATURE: $ENVELOPE"
```

**HTTP 200** returns {"letter_body": "Dear Bureau, ...", "cert_svg": "<svg>...</svg>", "timestamp": "...", "signature": "..."}.

## 3. Already settled but got no payload?

An EIP-3009 nonce is **at-most-once** — if you paid on-chain but the call failed
(crash, timeout, or an `already_settled` reply), the funds are not lost. The
fleet runs a claims desk: check **<https://settlement-collector.fly.dev/storefront/claims>** with your tx hash (live, verified
2026-11-15) and finish recovery at `/storefront/register` with your claim code
(format `RAEN-XXXXXXXXXX`).

Next: [Recipe 16 — tradingagents](16-tradingagents.md)
