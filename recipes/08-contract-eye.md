---
permalink: /recipes/08-contract-eye.md
---

# Recipe 08 — contract-eye: flag one-sided contract clauses

Paste contract text, get a risk analysis that flags risky, one-sided, or unusual clauses.

**Endpoint:** `POST https://contract-eye-x402.fly.dev/api/analyze-contract` · **Price:** **$0.005** USDC on Base (`eip155:8453`, scheme `exact`) — LIVE-VERIFIED 2026-11-25: `accepts[0].amount` = `5000`, canonical payTo (owner-approved 2026-11-24 ladder now serving). Bulk 10-99 @ $0.002, 100+ @ $0.001 · $0.001 probe. · **Challenge below decoded live from this endpoint: 2026-11-25**

## 1. Decode the 402 challenge (the 60-second test)

```bash
curl -s -D headers.txt -o body.json -X POST \
  https://contract-eye-x402.fly.dev/api/analyze-contract \
  -H 'Content-Type: application/json' \
  -d '{"text": "Buyer agrees to waive all claims. All fees are non-refundable. The company may terminate at any time without notice.", "focus": ["renewal", "liability"]}'
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
    "amount": "5000",
    "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "payTo": "0x9b8a27e03CEbA490953cDa8AB1291c0E13bAf72f",
    "maxTimeoutSeconds": 300,
    "extra": {
      "name": "USD Coin",
      "version": "2"
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
curl -s -X POST https://contract-eye-x402.fly.dev/api/analyze-contract \
  -H 'Content-Type: application/json' \
  -d '{...}' \
  -H "X-PAYMENT: $ENVELOPE"
```

**HTTP 200** returns a risk score, flagged clauses with severity / explanation / suggested edits, and a safe-clause summary.

## 3. Already settled but got no payload?

An EIP-3009 nonce is **at-most-once** — if you paid on-chain but the call failed
(crash, timeout, or an `already_settled` reply), the funds are not lost. The
fleet runs a claims desk: check **<https://settlement-collector.fly.dev/storefront/claims>** with your tx hash (live, verified
2026-11-15) and finish recovery at `/storefront/register` with your claim code
(format `RAEN-XXXXXXXXXX`).


`text` needs at least 40 characters (up to 50,000); `focus` is an optional
clause-category list. If LLM analysis is unavailable you get a deterministic
rule-based clause scan — the response's `method` and `delivery_mode` fields
disclose which ran.

Next: [Recipe 09 — briefsnap](09-briefsnap.md)
