# Pay with USDC — RAEN x402 developer documentation

Generated 2026-11-26T08:53:06.604379Z from LIVE surfaces by `developer-docs/1.0`. Every price, payTo, network and request shape below was read from a fresh unpaid 402 challenge and the seller's own manifest — no cached or hand-typed figures.

> Read this first: RAEN walls settle on **Base (eip155:8453)** in USDC. Payments use x402 with EIP-3009 (`transferWithAuthorization`) — no card, no account, no API key. Discovery is free; the call is paid.

## 1. Quickstart (3 steps)

1. **Discover** — `GET /.well-known/x402.json` on a wall. Free, no payment. Lists routes, request shapes and prices.
2. **Get a challenge** — send the request once with no payment. The wall replies `402 Payment Required` with a base64 `payment-required` header. Decode it to see `accepts[0]` (amount in USDC atomic units, payTo, network, scheme).
3. **Pay and retry** — sign an EIP-3009 `transferWithAuthorization` for exactly that amount/payTo/network, base64-encode it as `X-PAYMENT`, resend the same request. The wall settles on-chain and returns the deliverable (and a receipt).

## 2. API reference (live-verified)

| Service | Route | Method | Live price | Network | Scheme | payTo (canonical) |
|---|---|---|---|---|---|---|
| royal-ruby | `/api/law-lookup` | POST | $0.05 | eip155:8453 | exact | `0x9b8a27e03ceba490953cda8ab1291c0e13baf72f` |
| contract-eye | `/api/analyze-contract` | POST | $0.005 | eip155:8453 | exact | `0x9b8a27e03CEbA490953cDa8AB1291c0E13bAf72f` |
| gateway | `/mcp` | POST | $0.05 | eip155:8453 | exact | `0x9b8a27e03CEbA490953cDa8AB1291c0E13bAf72f` |

### royal-ruby — `/api/law-lookup`

- Request fields (seller's published example): `scope, state, topic`
- Example body: `{"topic":"credit-report disputes for collection accounts","state":"LA","scope":"both"}`
- Manifest HTTP 200, OpenAPI HTTP 200 (documented), live 402 HTTP 402

### contract-eye — `/api/analyze-contract`

- Request fields (seller's published example): `focus, text`
- Example body: `{"text":"This agreement auto-renews every twelve months unless cancelled sixty days prior.","focus":["renewal","liability"]}`
- Manifest HTTP 200, OpenAPI HTTP 200 (documented), live 402 HTTP 402

### gateway — `/mcp`

- Request fields (seller's published example): `id, jsonrpc, method, params`
- Example body: `{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"raen_law_lookup","arguments":{"query":"FCRA"}}}`
- Manifest HTTP 200, OpenAPI HTTP 200 (documented), live 402 HTTP 402
- Free discovery: tools/list (free, no challenge) — the route above is the paid wall.

## 3. Integration examples

### Example 1 — decode a live 402 challenge (curl + Python stdlib, no payment)
```bash
curl -s -D - -o /dev/null -X POST https://contract-eye-x402.fly.dev/api/analyze-contract \
  -H 'Content-Type: application/json' \
  -d '{"text":"auto-renews every 12 months","focus":["renewal"]}' \
  | grep -i '^payment-required:'
```

```python
import base64, json, urllib.request, urllib.error
req = urllib.request.Request(
    'https://contract-eye-x402.fly.dev/api/analyze-contract',
    data=b'{"text":"auto-renews every 12 months","focus":["renewal"]}',
    method='POST', headers={'Content-Type': 'application/json'})
try:
    urllib.request.urlopen(req)  # 200 would mean the route is not paid
except urllib.error.HTTPError as e:
    if e.code == 402:
        raw = e.headers['payment-required']
        challenge = json.loads(base64.b64decode(raw + '=' * (-len(raw) % 4)))
        a = challenge['accepts'][0]
        print('pay', a['amount'], 'atomic USDC to', a['payTo'], 'on', a['network'])
```

### Example 2 — attach X-PAYMENT and retry (illustrative; sign with YOUR wallet)
```python
import base64, json, urllib.request
# 1. decode the challenge as in Example 1 -> a = challenge['accepts'][0]
# 2. sign EIP-3009 transferWithAuthorization with YOUR key (never committed here).
#    amount = a['amount'], to = a['payTo'], asset = a['asset'], network = a['network'].
authorization = {'transferWithAuthorization': SIGNED_AUTHORIZATION}  # your signed payload
x_payment = base64.b64encode(json.dumps(authorization).encode()).decode()
req = urllib.request.Request(
    'https://contract-eye-x402.fly.dev/api/analyze-contract',
    data=b'{"text":"auto-renews every 12 months","focus":["renewal"]}',
    method='POST', headers={'Content-Type': 'application/json', 'X-PAYMENT': x_payment})
with urllib.request.urlopen(req) as r:
    print(r.status, r.read().decode())  # 200 + deliverable + receipt
```

### Example 3 — three-surface cross-check before wiring a wall
```python
import json, urllib.request
base = 'https://royal-ruby-x402.fly.dev'
manifest = json.load(urllib.request.urlopen(base + '/.well-known/x402.json'))
openapi = json.load(urllib.request.urlopen(base + '/openapi.json'))
route = '/api/law-lookup'
print('in manifest :', route in json.dumps(manifest))
print('in openapi  :', route in openapi.get('paths', {}))
print('manifest fields:', manifest.get('extensions', {}).get('bazaar', {}))
# Then decode a live 402 (Example 1) and confirm its payTo/network/amount
# match the manifest. A mismatch is DRIFT — report it, do not pay it.
```

## 4. Truth notes

- Price truth = a fresh live 402 challenge (accepts[0].amount), never a hand-typed or cached figure.
- payTo truth = the full 42-character canonical address, compared case-insensitively (homoglyph-safe).
- A 402 challenge is a demand signal, not a sale: most challenges are scanners/bots (Recipe 36).
- Internal self-pays (AgentCash) are not external revenue; fleet external revenue is $0.00 unless the chain says otherwise.
- On x402 paid walls the 402 precedes body validation: request shapes here are the seller's published manifest examples, not an observed validation result.
- Some surfaces expose a FREE discovery call that returns 200 with no challenge (e.g. gateway tools/list); the paid wall is tools/call.
- This pack verifies Base (eip155:8453) only — the chain RAEN walls settle on. Frozen services are never probed (BURN FREEZE).
- Code examples are illustrative: they contain NO real key and sign NOTHING. Payment happens only when the buyer attaches their own X-PAYMENT.

Verdict: **CLEAN** — live 402s canonical on all probed walls, 0 price drift.
