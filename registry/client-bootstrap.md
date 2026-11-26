# Machine-Buyer Client Bootstrap

Generated 2026-11-26T14:42:27.531968+00:00 - client-bootstrap/1.0. Every URL, price, payTo and network below is a LIVE-READ fact from an unpaid 402 challenge. No funds were moved to produce this.

| Wall | Endpoint | Live price | Network | Scheme | Canonical payTo |
|---|---|---|---|---|---|
| royal-ruby | `POST https://royal-ruby-x402.fly.dev/api/law-lookup` | $0.0050 | eip155:8453 | exact | yes |
| contract-eye | `POST https://contract-eye-x402.fly.dev/api/analyze-contract` | $0.0050 | eip155:8453 | exact | yes |
| nanobanana | `POST https://nanobanana-x402.fly.dev/api/generate-image` | $0.0100 | eip155:8453 | exact | yes |
| raen-mcp-gateway | `POST https://raen-mcp-gateway.fly.dev/mcp` | $0.0500 | eip155:8453 | exact | yes |

## Four-step flow (the only part a buyer must supply is their own signature)

1. **Unpaid call** -> receive the 402 `payment-required` header (base64 JSON).
2. **Decode** `accepts[0]`: `scheme`, `network`, `payTo`, `amount` (atomic USDC, 6 dp).
3. **Preflight assert** `payTo` equals the full canonical address (case-insensitive), `scheme=exact`, `network=eip155:8453`, `amount>0`. Never pay a lookalike.
4. **Sign with YOUR wallet** (EIP-3009 on Base) -> base64 `X-PAYMENT` -> retry the call. The bootstrap tool never signs; the skeleton below raises until you plug in a signer.

## Run-ready skeleton (stdlib; replace the signing stub)

```python
#!/usr/bin/env python3
# RAEN client bootstrap - generated live KEYWORDS, stdlib only.
# Every price/payTo/network below is a LIVE-READ fact from an unpaid 402.
# This skeleton NEVER signs and NEVER spends on its own: step 2 calls a stub you
# must replace with YOUR wallet's x402 signer. Verify payTo before paying.
import json, base64, urllib.request, urllib.error

CANON = "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f"
WALLS = {
  "royal-ruby": {
    "url": "https://royal-ruby-x402.fly.dev/api/law-lookup",
    "method": "POST",
    "request_body": {
      "query": "x402 bootstrap probe"
    },
    "http_status": 402,
    "live_price_usd": 0.005,
    "amount_atomic": 5000,
    "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "scheme": "exact",
    "network": "eip155:8453",
    "payTo": "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f",
    "canonical": true,
    "checks": {
      "v2": true,
      "scheme": true,
      "network": true,
      "payTo": true,
      "amount": true
    },
    "detail": "canonical"
  },
  "contract-eye": {
    "url": "https://contract-eye-x402.fly.dev/api/analyze-contract",
    "method": "POST",
    "request_body": {
      "text": "x402 bootstrap probe"
    },
    "http_status": 402,
    "live_price_usd": 0.005,
    "amount_atomic": 5000,
    "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "scheme": "exact",
    "network": "eip155:8453",
    "payTo": "0x9b8a27e03CEbA490953cDa8AB1291c0E13bAf72f",
    "canonical": true,
    "checks": {
      "v2": true,
      "scheme": true,
      "network": true,
      "payTo": true,
      "amount": true
    },
    "detail": "canonical"
  },
  "nanobanana": {
    "url": "https://nanobanana-x402.fly.dev/api/generate-image",
    "method": "POST",
    "request_body": {
      "prompt": "x402 bootstrap probe"
    },
    "http_status": 402,
    "live_price_usd": 0.01,
    "amount_atomic": 10000,
    "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "scheme": "exact",
    "network": "eip155:8453",
    "payTo": "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f",
    "canonical": true,
    "checks": {
      "v2": true,
      "scheme": true,
      "network": true,
      "payTo": true,
      "amount": true
    },
    "detail": "canonical"
  },
  "raen-mcp-gateway": {
    "url": "https://raen-mcp-gateway.fly.dev/mcp",
    "method": "POST",
    "request_body": {
      "jsonrpc": "2.0",
      "id": 1,
      "method": "tools/call",
      "params": {
        "name": "raen_law_lookup",
        "arguments": {
          "topic": "x402 bootstrap probe"
        }
      }
    },
    "http_status": 402,
    "live_price_usd": 0.05,
    "amount_atomic": 50000,
    "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "scheme": "exact",
    "network": "eip155:8453",
    "payTo": "0x9b8a27e03CEbA490953cDa8AB1291c0E13bAf72f",
    "canonical": true,
    "checks": {
      "v2": true,
      "scheme": true,
      "network": true,
      "payTo": true,
      "amount": true
    },
    "detail": "canonical"
  }
}


def unpaid(choice):
    """Step 1 - unpaid call. The seller's 402 challenge is the source of truth."""
    w = WALLS[choice]
    req = urllib.request.Request(
        w["url"], data=json.dumps(w["body"]).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "User-Agent": "raen-client-bootstrap/1.0"},
        method=w["method"])
    try:
        urllib.request.urlopen(req, timeout=20)
        raise RuntimeError("expected a 402 challenge, got 2xx (is this route free?)")
    except urllib.error.HTTPError as e:
        if e.code != 402:
            raise
        raw = (e.headers.get("payment-required")
               or e.headers.get("x-payment-required") or "")
        if "," in raw and not raw.lstrip().startswith("{"):
            raw = raw.split(",", 1)[1].strip()
        obj = json.loads(base64.b64decode(raw + "=" * (-len(raw) % 4)))
        return obj, w


def build_payment_header(challenge):
    """Step 2a - build the X-PAYMENT payload. YOU supply the signature.

    The RAEN bootstrap tool never signs and never touches a wallet. Plug in an
    x402 signer (EIP-3009 transferWithAuthorization on Base) that produces the
    base64 header the seller's accepts[] entry describes.
    """
    a = challenge["accepts"][0]
    assert a["payTo"].lower() == CANON.lower(), "NON-CANONICAL payTo - DO NOT PAY"
    assert a["scheme"] == "exact" and a["network"] == "eip155:8453", "wrong scheme/network"
    assert int(a["amount"]) > 0, "invalid amount"
    # TODO: sign with YOUR wallet. Return the base64 X-PAYMENT header string.
    raise NotImplementedError("connect your own x402 signer (EIP-3009 on Base)")


def paid(choice):
    """Step 2b - retry with the signed header and read the deliverable."""
    challenge, w = unpaid(choice)
    header = build_payment_header(challenge)  # base64 X-PAYMENT from your signer
    req = urllib.request.Request(
        w["url"], data=json.dumps(w["body"]).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-PAYMENT": header},
        method=w["method"])
    return urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "replace")


if __name__ == "__main__":
    import sys
    choice = sys.argv[1] if len(sys.argv) > 1 else "royal-ruby"
    print(paid(choice))

```

Canonical payTo: `0x9b8a27e03ceba490953cda8ab1291c0e13baf72f`. A wall whose `Canonical payTo` column reads NO is a payment-path break - do not pay it; the live 402 of a canonical wall is always authoritative over any hand-maintained price table.
