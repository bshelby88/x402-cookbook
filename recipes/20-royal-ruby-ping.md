---
permalink: /recipes/20-royal-ruby-ping.md
---

# Recipe 20 — royal-ruby ping: the $0.001 alive-check

The cheapest settled liveness probe in the x402 ecosystem. One GET, **$0.001**
(1000 atomic USDC units) on Base, and you get machine-checkable proof of life:
`{status:'alive', block, latency_ms, catalog_url}` — the current Base block
number, server latency, and the service's manifest URL. Built for crawlers,
uptime watchers, and machine payers that want a one-atom probe with real
settlement instead of a free ping that proves nothing.

**Endpoint:** `GET https://royal-ruby-x402.fly.dev/api/ping` · **Price:** $0.001 USDC on Base (`eip155:8453`, scheme `exact`) · **Challenge below decoded live from this endpoint: 2026-11-25**

## 1. Decode the 402 challenge (the 10-second test)

```bash
curl -s -D headers.txt -o body.json https://royal-ruby-x402.fly.dev/api/ping
```

You get **HTTP 402 Payment Required** — the challenge rides in the
`payment-required` header (base64 JSON), mirrored in the body. Decode:

```bash
python - <<'EOF'
import base64, json
val = open("headers.txt").read().split("payment-required:", 1)[1].splitlines()[0].strip()
val += "=" * (-len(val) % 4)          # tolerate stripped padding
print(json.dumps(json.loads(base64.b64decode(val)), indent=2))
EOF
```

A live challenge from this exact endpoint (decoded from the wire **2026-11-25**) — amounts are
atomic USDC units (6 decimals), so `accepts[0].amount` = `1000` = $0.001. The response is an
**x402 v2 envelope**; `amount` lives at `accepts[0].amount`, NOT at the top level. Extension
metadata (`extensions.bazaar`) is omitted here for brevity; the payment-contract fields are
verbatim:

```json
{
  "x402Version": 2,
  "error": "Payment required",
  "resource": {
    "url": "https://royal-ruby-x402.fly.dev/api/ping",
    "mimeType": "application/json"
  },
  "accepts": [
    {
      "scheme": "exact",
      "network": "eip155:8453",
      "amount": "1000",
      "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
      "payTo": "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f",
      "maxTimeoutSeconds": 300,
      "extra": { "name": "USD Coin", "version": "2" }
    }
  ]
}
```

## 2. Pay and retry (settle → retry → 200)

Sign the challenge with any x402 client (Recipe [02-python-client](02-python-client.md)
or the [x402 SDK](https://x402.org)) and repeat the GET with the payment header:

```bash
# with raen-call (signs with your local wallet):
raen-call get https://royal-ruby-x402.fly.dev/api/ping --pay

# or with the x402-fetch / Go client / any x402-enabled agent wallet —
# the 402 challenge above is the exact payment contract.
curl -s https://royal-ruby-x402.fly.dev/api/ping \
  -H "X-PAYMENT: <base64 x402 v2 payload signed by your EOA>"
```

**200 response shape** (published in the manifest's bazaar extension):

```json
{
  "status": "alive",
  "block": 27431025,
  "latency_ms": 12,
  "catalog_url": "https://royal-ruby-x402.fly.dev/.well-known/x402.json"
}
```

- `status` is always `"alive"` on a 200 — the probe's only contract is liveness truth.
- `block` is the current Base mainnet block (never fabricated; `null` only if
  every public RPC failed — still means alive).
- `latency_ms` is server-side response time.
- `catalog_url` points at the live manifest so a crawler can chain straight
  from one ping into the full priced catalog.

## 3. Machine verification checklist

1. `accepts[0].amount` must be exactly `"1000"` (any other amount = not this SKU; the
   price field is inside the x402 v2 envelope, never top-level — see
   [Recipe 23](23-buyer-preflight.md)).
2. `payTo` must be the canonical treasury `0x9b8a27e03ceba490953cda8ab1291c0e13baf72f`.
3. `network` must be `eip155:8453` (Base mainnet USDC).
4. After settling, the response carries a payment-response header with the
   settle tx — verify on-chain like any other x402 call (Recipe [01](01-curl-402-decode.md)).

The full machine contract (input schema + output example) is published in the
x402 manifest under `endpoints./api/ping.extensions.bazaar`:
`GET https://royal-ruby-x402.fly.dev/.well-known/x402.json`

## Where to go next

- Buying for a machine that doesn't read email? Register your purchase by
  webhook: `POST https://settlement-collector.fly.dev/storefront/register`
  with `{tx_or_intent, agent_id, callback_url}` — receipt + claims arrive as
  an HTTP POST instead of email.
- Free-machine onboarding docs: `https://settlement-collector.fly.dev/clearing/catalog.json`
  (the `/clearing/intent` envelope's `step_7_machine_registration`).
