---
permalink: /recipes/11-nft-alpha.md
---

# Recipe 11 — nft-alpha: OpenSea market signals on Base

Live OpenSea market signals for watched NFT collections: listings, sales, bids, floor pressure, sell-through, bid frenzy.

**Endpoint:** `POST https://nft-alpha-x402.fly.dev/api/nft-signal` · **Price:** $0.02 USDC on Base (`eip155:8453`, scheme `exact`) · **Challenge below decoded live from this endpoint: 2026-11-15**

## 1. Decode the 402 challenge (the 60-second test)

```bash
curl -s -D headers.txt -o body.json -X POST \
  https://nft-alpha-x402.fly.dev/api/nft-signal \
  -H 'Content-Type: application/json' \
  -d '{"collection": "pudgypenguins"}'
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
    "amount": "20000",
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

## 2. Settle and retry

1. **Settle:** pay `amount` of USDC to `payTo` on Base and sign an EIP-3009
   `transferWithAuthorization` envelope built from this challenge — bring your
   own signer or use the [x402 SDK](https://github.com/coinbase/x402). Full
   client walkthrough: [Recipe 02](02-python-client.md).
2. **Retry the identical POST** with the envelope:

```bash
curl -s -X POST https://nft-alpha-x402.fly.dev/api/nft-signal \
  -H 'Content-Type: application/json' \
  -d '{...}' \
  -H "PAYMENT-SIGNATURE: $ENVELOPE"
```

**HTTP 200** returns 5-minute-fresh signal JSON: listings, sales, bids, floor pressure, sell-through, bid frenzy.

## 3. Already settled but got no payload?

An EIP-3009 nonce is **at-most-once** — if you paid on-chain but the call failed
(crash, timeout, or an `already_settled` reply), the funds are not lost. The
fleet runs a claims desk: check **<https://settlement-collector.fly.dev/storefront/claims>** with your tx hash (live, verified
2026-11-15) and finish recovery at `/storefront/register` with your claim code
(format `RAEN-XXXXXXXXXX`).


Batch 1–10 collections with `{"collections": ["azuki", "pudgypenguins"]}`.
Currently watched slugs: `boredapeyachtclub`, `mutant-ape-yacht-club`, `azuki`,
`pudgypenguins`, `milady`, `doodles-official`, `degods`, `cryptopunks`.

Next: [Recipe 12 — vault-pro](12-vault-pro.md)
