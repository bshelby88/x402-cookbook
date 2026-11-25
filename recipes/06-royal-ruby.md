---
permalink: /recipes/06-royal-ruby.md
---

# Recipe 06 — royal-ruby: consumer-law citations

FCRA / FDCPA / TILA / state-UDAP statute citations for a consumer-rights question — and your **first call is free** (charge-and-rebate, net $0).

**Endpoint:** `POST https://royal-ruby-x402.fly.dev/api/law-lookup` · **Price:** **$0.005** USDC on Base (`eip155:8453`, scheme `exact`) — owner-approved 2026-11-24 ladder price; the repriced deploy is rolling out, and until it lands your live 402 challenge shows the pre-ladder price ($0.05 / $0.03 A/B) and is authoritative. Bulk 10-99 @ $0.002, 100-500 @ $0.001 (floor 10) · $0.001 probe at `/api/ping` (live). · **Challenge below decoded live from this endpoint: 2026-11-15**

## 1. Decode the 402 challenge (the 60-second test)

```bash
curl -s -D headers.txt -o body.json -X POST \
  https://royal-ruby-x402.fly.dev/api/law-lookup \
  -H 'Content-Type: application/json' \
  -d '{}'
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
    "payTo": "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f",
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
curl -s -X POST https://royal-ruby-x402.fly.dev/api/law-lookup \
  -H 'Content-Type: application/json' \
  -d '{}' \
  -H "X-PAYMENT: $ENVELOPE"
```

**HTTP 200** returns {"ok": true, "result": {"federal_citations": [...], "timelines": [...], "statute_of_limitations": {...}}}.

## 3. Already settled but got no payload?

An EIP-3009 nonce is **at-most-once** — if you paid on-chain but the call failed
(crash, timeout, or an `already_settled` reply), the funds are not lost. The
fleet runs a claims desk: check **<https://settlement-collector.fly.dev/storefront/claims>** with your tx hash (live, verified
2026-11-15) and finish recovery at `/storefront/register` with your claim code
(format `RAEN-XXXXXXXXXX`).


## Free first call (this SKU only)

Send one extra header on the paid call: `x-payer-address: 0xYourWalletAddress`.
You pay the normal challenge; the service rebates the full amount right after
settlement — net $0, one per wallet per 30 days. Full walkthrough:
[Recipe 03](03-free-first-call.md). Disclosed price experiment: some wallets see
$0.03 — whatever amount your challenge shows is what you pay. (The A/B bucket experiment ends under the 2026-11-24 ladder: both buckets see $0.005 once the repriced deploy lands.)

If the LLM enhancer is offline you still get a deterministic statutory baseline
(`mode: statutory-baseline`) with verified core citations.

Next: [Recipe 07 — dispatch](07-dispatch.md)
