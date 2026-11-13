# Recipe 02 — Python: a generic paid-call client

A ~40-line client that works for any RAEN fleet service: fetch the 402 challenge,
settle it, retry the call.

```python
"""Minimal x402 paid-call client (Base mainnet, USDC, scheme=exact)."""
import base64, json, os, requests

def challenge(resp):
    """Read the 402 challenge from the body (preferred) or payment-required header."""
    if resp.headers.get("payment-required"):
        val = resp.headers["payment-required"].strip()
        val += "=" * (-len(val) % 4)
        return json.loads(base64.b64decode(val))
    return resp.json()  # quote-fix services mirror the challenge in the body

def pay_and_call(url: str, body: dict, signer) -> dict:
    # 1) unpaid POST -> 402 challenge
    r = requests.post(url, json=body)
    if r.status_code != 402:
        return r.json()
    c = challenge(r)
    req = c["accepts"][0]

    # 2) settle: USDC transfer of req["amount"] to req["payTo"] on Base,
    #    signed as an EIP-3009 envelope against the challenge.
    #    `signer` is any EIP-3009 implementation — bring your own or use
    #    the official x402 SDK: https://github.com/coinbase/x402
    envelope = signer.sign_challenge(c)

    # 3) retry with payment
    r2 = requests.post(url, json=body, headers={
        "PAYMENT-SIGNATURE": envelope,   # some stacks accept x-payment
    })
    return r2.json()
```

Notes:

- **Bring your own signer.** The network leg is an ordinary USDC transfer on Base
  (`0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`, 6 decimals — `50000` = $0.05) plus an
  EIP-3009 signature derived from the challenge. The [x402 SDK](https://github.com/coinbase/x402)
  ships a ready signer if you don't want to hand-roll one.
- **`x-payer-address`:** on services with charge-and-rebate (royal-ruby), send your
  wallet as an `x-payer-address` header on the *paid* call — that's the address the
  rebate is sent back to. See [Recipe 03](03-free-first-call.md).
- **Verify before paying:** every fleet service serves its price and payTo at
  `/.well-known/x402.json` — always confirm the live manifest before settling.
- **Free previews:** `dispatch-x402.fly.dev/classify` and `settlement-collector.fly.dev/stats`
  are free — no payment needed.

Next: [Recipe 03 — free first call](03-free-first-call.md).
