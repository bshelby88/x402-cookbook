---
permalink: /recipes/15-dispute-forge.md
---

# Recipe 15 — dispute-forge: dispute letter + on-chain certificate

An FCRA-compliant dispute letter plus a unique SVG certificate of dispute, signed and timestamped.

**Endpoint:** `POST https://dispute-forge-x402.fly.dev/api/dispute-pack` · **Price:** **$0.01** USDC on Base (`eip155:8453`, scheme `exact`) — owner-approved 2026-11-24 ladder price, **LIVE-VERIFIED 2026-11-25** (`accepts[0].amount` = `10000`). Bulk 10+ @ $0.005 · $0.001 probe. · **Challenge below decoded live from this endpoint: 2026-11-25**

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

A live challenge from this exact endpoint (decoded from the wire **2026-11-25**) — **pay exactly
what your challenge says**; amounts are atomic USDC units (6 decimals). The live
`accepts[0].amount` is `10000` = **$0.01** (the 2026-11-24 ladder price is now serving on this
route). The response is an **x402 v2 envelope**: the requirement object lives inside `accepts[]`,
NOT at the top level. Extension metadata (`extensions.bazaar`) is omitted here for brevity;
the fields that form the payment contract are reproduced verbatim. If your decode shows
anything else, trust your decode:

```json
{
  "x402Version": 2,
  "error": "Payment required",
  "resource": {
    "url": "https://dispute-forge-x402.fly.dev/api/dispute-pack",
    "mimeType": "application/json",
    "serviceName": "dispute-forge"
  },
  "accepts": [
    {
      "scheme": "exact",
      "network": "eip155:8453",
      "amount": "10000",
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
}
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
  -H "X-PAYMENT: $ENVELOPE"
```

**HTTP 200** returns {"letter_body": "Dear Bureau, ...", "cert_svg": "<svg>...</svg>", "timestamp": "...", "signature": "..."}.

**Header name is `X-PAYMENT`.** Verified end-to-end with x402 SDK v2.30 on a real $0.001
settle (`tx 0x03a014da1fe7743809b3e3c6653ea1cebd0030474305bfda1b07508ac7f28cd5`).
An older draft of this recipe said `PAYMENT-SIGNATURE`; a probe with that header name gets a
fresh 402 with no error discrimination, so it is NOT a reliable retry path. Treat `X-PAYMENT`
as the RAEN-verified path, and use [Recipe 23 — buyer preflight](23-buyer-preflight.md) to
verify a wall before you sign.

## 3. Already settled but got no payload?

An EIP-3009 nonce is **at-most-once** — if you paid on-chain but the call failed
(crash, timeout, or an `already_settled` reply), the funds are not lost. The
fleet runs a claims desk: check **<https://settlement-collector.fly.dev/storefront/claims>** with your tx hash (live, verified
2026-11-15) and finish recovery at `/storefront/register` with your claim code
(format `RAEN-XXXXXXXXXX`).

Next: [Recipe 16 — tradingagents](16-tradingagents.md)
