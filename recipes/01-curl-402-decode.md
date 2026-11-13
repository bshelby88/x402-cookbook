---
permalink: /recipes/01-curl-402-decode.md
---

# Recipe 01 — curl: decode your first 402 challenge

Understand the x402 protocol in 60 seconds. No wallet needed for this step — you just
read the price tag.

## 1. Call a paid endpoint with no payment

```bash
curl -s -D headers.txt -o body.json -X POST \
  https://royal-ruby-x402.fly.dev/api/law-lookup \
  -H 'Content-Type: application/json' \
  -d '{}'
```

You get **HTTP 402 Payment Required**. The challenge rides in the `payment-required`
response header (base64 JSON) — and on current fleet services the same JSON is also in
the response body, so you can read it with plain JSON tooling.

## 2. Decode the challenge

```bash
python - <<'EOF'
import base64, json
# from the payment-required response header:
val = open("headers.txt").read().split("payment-required:", 1)[1].splitlines()[0].strip()
val += "=" * (-len(val) % 4)          # tolerate stripped padding
print(json.dumps(json.loads(base64.b64decode(val)), indent=2))
EOF
```

A live challenge looks like this (captured from royal-ruby, Nov 2026):

```json
{
  "x402Version": 2,
  "resource": {
    "url": "https://royal-ruby-x402.fly.dev/api/law-lookup",
    "mimeType": "application/json"
  },
  "accepts": [
    {
      "scheme": "exact",
      "network": "eip155:8453",
      "amount": "50000",
      "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
      "payTo": "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f",
      "maxTimeoutSeconds": 300
    }
  ]
}
```

Reading it:

| Field | Meaning |
|---|---|
| `scheme: exact` | pay exactly `amount` of the named asset — no more, no less |
| `network: eip155:8453` | Base mainnet |
| `amount: 50000` | atomic USDC units → $0.05 (USDC has 6 decimals) |
| `asset` | official USDC contract on Base |
| `payTo` | the address that receives the payment |

## 3. The two-POST flow

1. **POST without payment** → 402 + challenge (what you just did).
2. **Pay** the `amount` of USDC to `payTo` on Base and build an EIP-3009
   payment-signature envelope from the challenge.
3. **Resend the same POST** with the signed envelope in the `PAYMENT-SIGNATURE`
   (or `x-payment`) header → HTTP 200 with the real output.

That's the entire protocol: one 402, one transfer, one retry.

## Tip: machine-readable quotes on GET

Paid routes also answer a bare **GET** with a 402 quote body (no challenge header,
never settles) so agents can price a call without triggering the full challenge:

```bash
curl -s https://royal-ruby-x402.fly.dev/api/law-lookup | python -m json.tool
# -> {"quote": {"price": "$0.05 per call", "network": "eip155:8453", ...}}
```

Next: [Recipe 02 — a generic paid-call client](02-python-client.md).
