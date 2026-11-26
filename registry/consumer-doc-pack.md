# RAEN consumer documentation pack — verified first-call facts

Generated 2026-11-26T07:40:00.465394+00:00 by `consumer-doc-pack/1.0`. Every price, address and request shape below was read from a **live** surface this run — nothing is hand-typed.

## Before you pay

- Price truth is the live HTTP 402 challenge, not this page and not any cached price.
- Pay the **canonical** address in full: `0x9b8a27e03ceba490953cda8ab1291c0e13baf72f` on **Base (eip155:8453)**, scheme `exact`, USDC `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`.
- An unpaid POST returns 402 with a `payment-required` header (base64 JSON). Decode `accepts[0]`, pay with `X-PAYMENT`, retry the POST.
- A 402 is a challenge, not a sale. Most challenge volume here is scanners/bots. External earned revenue is **$0.00** unless the chain says otherwise.
- Frozen services are not covered here; only kept-live walls are listed.

## Verified walls

### royal-ruby — `POST /api/law-lookup`

- Base URL: `https://royal-ruby-x402.fly.dev`
- Live price: **$0.05** USDC (`accepts[0].amount = 50000`)
- Pay-to: `0x9b8a27e03ceba490953cda8ab1291c0e13baf72f` (CANONICAL)
- Network / scheme: `eip155:8453` / `exact`
- Manifest: HTTP 200; OpenAPI: HTTP 200; advertised price: not published in manifest — live 402 is authoritative
- Request body (source: `extensions.bazaar.info.input.body`):

```json
{
  "topic": "credit-report disputes for collection accounts",
  "state": "LA",
  "scope": "both"
}
```

```bash
curl -s -X POST 'https://royal-ruby-x402.fly.dev/api/law-lookup' -H 'Content-Type: application/json' -d '{"topic": "credit-report disputes for collection accounts", "state": "LA", "scope": "both"}' -i   # -> 402; decode payment-required, then retry with X-PAYMENT
```

### contract-eye — `POST /api/analyze-contract`

- Base URL: `https://contract-eye-x402.fly.dev`
- Live price: **$0.005** USDC (`accepts[0].amount = 5000`)
- Pay-to: `0x9b8a27e03CEbA490953cDa8AB1291c0E13bAf72f` (CANONICAL)
- Network / scheme: `eip155:8453` / `exact`
- Manifest: HTTP 200; OpenAPI: HTTP 200; advertised price: $0.005 (accepts.price)
- Request body (source: `extensions.bazaar.info.input.body`):

```json
{
  "text": "This agreement auto-renews every twelve months unless cancelled sixty days prior.",
  "focus": [
    "renewal",
    "liability"
  ]
}
```

```bash
curl -s -X POST 'https://contract-eye-x402.fly.dev/api/analyze-contract' -H 'Content-Type: application/json' -d '{"text": "This agreement auto-renews every twelve months unless cancelled sixty days prior.", "focus": ["renewal", "liability"]}' -i   # -> 402; decode payment-required, then retry with X-PAYMENT
```

### gateway — `POST /mcp`

- Base URL: `https://raen-mcp-gateway.fly.dev`
- Live price: **$0.05** USDC (`accepts[0].amount = 50000`)
- Pay-to: `0x9b8a27e03CEbA490953cDa8AB1291c0E13bAf72f` (CANONICAL)
- Network / scheme: `eip155:8453` / `exact`
- Manifest: HTTP 200; OpenAPI: HTTP 200; advertised price: $0.05 (accepts.amount)
- Request body (source: `fallback_known_good`):

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "raen_law_lookup",
    "arguments": {
      "query": "FCRA"
    }
  }
}
```

```bash
curl -s -X POST 'https://raen-mcp-gateway.fly.dev/mcp' -H 'Content-Type: application/json' -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "raen_law_lookup", "arguments": {"query": "FCRA"}}}' -i   # -> 402; decode payment-required, then retry with X-PAYMENT
```

## Honest limits

- Route-level input validation could not be observed unpaid: the 402 challenge precedes body validation on these walls. Request shapes above are the seller's own published manifest examples, not a claim about server-side validation.
- This pack verifies Base only; no other chain is asserted.
- Nothing here was published externally; this is a local, read-only artifact.

MIT licensed. Not legal or financial advice.
