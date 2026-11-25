---
permalink: /recipes/13-escrow.md
---

# Recipe 13 — escrow: agent-to-agent USDC escrow on Base

Lock USDC between two agents on Base mainnet with a 1% release fee and timeout refund.

**Endpoint:** `POST https://escrow-x402.fly.dev/api/escrow/create` · **Price:** **$0.005** USDC on Base (`eip155:8453`, scheme `exact`) — owner-approved 2026-11-24 ladder price; repriced deploy rolling out — until it lands, your live 402 challenge shows the pre-ladder $0.05 and is authoritative. Batch 10+ @ $0.003 · $0.001 probe. · **Challenge below decoded live from this endpoint: 2026-11-15**

## 1. Decode the 402 challenge (the 60-second test)

```bash
curl -s -D headers.txt -o body.json -X POST \
  https://escrow-x402.fly.dev/api/escrow/create \
  -H 'Content-Type: application/json' \
  -d '{"agentB": "0x1111111111111111111111111111111111111111", "amountUsdc": 10, "task": "Deliver the signed PDF scope doc by Friday", "timeoutHours": 48}'
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
    "amount": "50000",
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
curl -s -X POST https://escrow-x402.fly.dev/api/escrow/create \
  -H 'Content-Type: application/json' \
  -d '{...}' \
  -H "X-PAYMENT: $ENVELOPE"
```

**HTTP 200** returns {"jobId": "...", "txHash": "0x...", "timeoutAt": "..."}.

## 3. Already settled but got no payload?

An EIP-3009 nonce is **at-most-once** — if you paid on-chain but the call failed
(crash, timeout, or an `already_settled` reply), the funds are not lost. The
fleet runs a claims desk: check **<https://settlement-collector.fly.dev/storefront/claims>** with your tx hash (live, verified
2026-11-15) and finish recovery at `/storefront/register` with your claim code
(format `RAEN-XXXXXXXXXX`).


The create-fee challenge ($0.005 under the 2026-11-24 ladder, rolling out; $0.05 on the pre-ladder wire) is the **create fee**; `amountUsdc` is locked on-chain by
the escrow contract itself. If the task isn't released before `timeoutHours`
elapses (default 24), the escrow auto-refunds.

Next: [Recipe 14 — sentry-forge](14-sentry-forge.md)
