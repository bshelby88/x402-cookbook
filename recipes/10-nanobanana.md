---
permalink: /recipes/10-nanobanana.md
---

# Recipe 10 — nanobanana: generate an image for $0.01

> **Pricing unchanged (2026-11-24 ladder):** single stays $0.01 (real per-call model cost). NEW: bulk 10+ @ $0.008/image and a $0.001 liveness ack (no image bytes) are part of the approved ladder and rolling out.

Gemini image generation from a text prompt — the cheapest paid call on the fleet.

**Endpoint:** `POST https://nanobanana-x402.fly.dev/api/generate-image` · **Price:** $0.01 USDC on Base (`eip155:8453`, scheme `exact`) · **Challenge below decoded live from this endpoint: 2026-11-15**

## 1. Decode the 402 challenge (the 60-second test)

```bash
curl -s -D headers.txt -o body.json -X POST \
  https://nanobanana-x402.fly.dev/api/generate-image \
  -H 'Content-Type: application/json' \
  -d '{"prompt": "A neon terminal style product hero image", "aspectRatio": "16:9"}'
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
    "amount": "10000",
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
curl -s -X POST https://nanobanana-x402.fly.dev/api/generate-image \
  -H 'Content-Type: application/json' \
  -d '{...}' \
  -H "X-PAYMENT: $ENVELOPE"
```

**HTTP 200** returns JSON containing the image as a base64 PNG.

## 3. Already settled but got no payload?

An EIP-3009 nonce is **at-most-once** — if you paid on-chain but the call failed
(crash, timeout, or an `already_settled` reply), the funds are not lost. The
fleet runs a claims desk: check **<https://settlement-collector.fly.dev/storefront/claims>** with your tx hash (live, verified
2026-11-15) and finish recovery at `/storefront/register` with your claim code
(format `RAEN-XXXXXXXXXX`).


`aspectRatio` accepts `1:1`, `16:9`, `9:16`, `3:2`, `2:3`, `4:3`, `3:4`, `4:5`,
`5:4`, `21:9` (default `1:1`). Save the PNG out of the 200 response:

```bash
python - <<'EOF'
import base64, json
data = json.load(open("body.json"))          # the HTTP 200 response
png = base64.b64decode(data.get("image") or data.get("imageBase64") or "")
open("out.png", "wb").write(png)
EOF
```

Next: [Recipe 11 — nft-alpha](11-nft-alpha.md)
