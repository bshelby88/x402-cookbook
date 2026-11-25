---
permalink: /recipes/27-buyer-receipt.md
---

# Recipe 27 — Buyer receipt: prove your x402 payment landed on Base

**Innovation 2026-11-25 (Tiffany, machine-buyer acquisition).** Recipes 23–26 help an agent decide *whether and where* to pay; recipes 21–22 cover delivery and claims. None let a buyer **prove, from the chain alone, that the money actually reached RAEN**. A seller's dashboard is not evidence (TRUTH law). An autonomous agent that can verify its own settlement without trusting the seller is an agent that will complete the first paid call — so this is an acquisition tool, not just a debugging aid.

This ships `scripts/receipt-verifier.py`: a free, read-only, stdlib-only script that takes a transaction hash, reads the receipt from a public Base RPC, decodes the ERC-20 USDC `Transfer` logs, and confirms the settlement reached the **canonical** payTo with the expected amount. It never signs, never builds a payment header, never sends funds, and never moves money.

## Why it matters to a machine buyer

- **No trust in the seller required.** Chain state is the money truth. The verifier decodes `eth_getTransactionReceipt` directly; it does not call any RAEN service.
- **Poison-safe.** A full 42-character, case-insensitive comparison against canonical `0x9b8a27e03ceba490953cda8ab1291c0e13baf72f` — homoglyph addresses cannot pass. Only USDC (`0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`) transfers count.
- **Amount-aware.** `--expect-amount` fails the check if the transfer came up short (partial payment, wrong route, fee surprise).
- **Scope-honest.** This proves *settlement*, not *delivery*. If the payment landed but the product never arrived, that is the [claims desk](22-claims-desk.md) (recipe 22). Chain-coverage law: this verifies **Base (`eip155:8453`)** only — the chain RAEN's x402 walls settle on.

## Install

No dependencies. Python 3 + `curl` (or point `--rpc` at any Base JSON-RPC).

## Usage

```bash
# Verify a settlement landed on canonical payTo
python3 scripts/receipt-verifier.py 0x39ac4545c1fe8c4f795a1ff3562ecf8bbb0dd6c43ac4fa92507b9f7c908d0182

# Also require that at least 0.05 USDC arrived (the royal-ruby price)
python3 scripts/receipt-verifier.py 0x39ac...0182 --expect-amount 0.05

# Use a different Base RPC
python3 scripts/receipt-verifier.py 0x39ac...0182 --rpc https://base.publicnode.com
```

## Real verified output (2026-11-25, live chain read)

A real internal test settle from the collector ledger (royal-ruby `/api/law-lookup`, $0.05):

```json
{
  "verified": true,
  "status": "VERIFIED",
  "chain": "eip155:8453 (Base)",
  "tx": "0x39ac4545c1fe8c4f795a1ff3562ecf8bbb0dd6c43ac4fa92507b9f7c908d0182",
  "block": "0x3aafe80",
  "tx_success": true,
  "from": "0xe72f0af4cf41356d433723547f1412ca27fbb1b8",
  "canonical_payto": "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f",
  "usdc_transfer_count": 1,
  "usdc_to_canonical": 0.05,
  "transfers": [
    {
      "from": "0xfbc0eb7811d477e55261d956df39f0046e192240",
      "to": "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f",
      "amount_usdc": 0.05,
      "to_canonical": true
    }
  ],
  "note": "USDC settlement to canonical payTo confirmed on Base"
}
```

Note the distinction the verifier makes visible: the **transaction** sender is the facilitator/bundler (`0xe72f0a…`), while the **ERC-20 Transfer** sender is the actual payer (AgentCash `0xfbc0…92240`). The verifier reports both so an agent can reconcile a payment against its own wallet even when a facilitator submits the transaction.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | `VERIFIED` — tx succeeded and USDC reached canonical payTo (≥ expected amount) |
| 1 | `NOT_VERIFIED` — tx failed, no canonical transfer, or short amount; see `reason[]` |
| 2 | `TRANSPORT` — bad hash, tx not found (wrong chain/pending), or RPC unreachable |

## The full buyer journey, now complete

1. Which wall? → [Recipe 26, Pick My Paywall](26-paywall-picker.md)
2. Is the wall legit before I sign? → [Recipe 23, buyer preflight](23-buyer-preflight.md)
3. What does it cost? → [Recipe 24, fleet price oracle](24-fleet-price-oracle.md)
4. Am I using the right header? → [Recipe 25, header conformance](25-payment-header-conformance.md) — the retry header is **`X-PAYMENT`** (not the stale `PAYMENT-SIGNATURE`)
5. Pay → [Recipe 01](01-curl-402-decode.md) / [Recipe 02](02-python-client.md)
6. **Did my payment land? → this recipe (27)**
7. Did I get the product? → [Recipe 22, claims desk](22-claims-desk.md)

Snapshot of the live verification: `registry/buyer-receipt-verification.json`.
