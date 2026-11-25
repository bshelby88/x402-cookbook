# Recipe 24 — Fleet price oracle (read-only live-402 decoder)

**Audience:** autonomous machine buyers, integrators, and any agent that needs
to know the *actual* price and payee of a RAEN wall before spending a cent.

**Problem it closes:** docs drift. A manifest, a recipe, or a marketplace
listing can say one price while the live 402 wire says another. The live
challenge is the only truth that determines what you will pay. Recipe 23
(`buyer-preflight.py`) verifies a single wall; this recipe verifies the whole
fleet in one pass and emits a machine-readable price sheet.

## Run it

```bash
python3 scripts/fleet-price-oracle.py --out registry/fleet-price-sheet.json
```

Stdlib only. No API keys, no wallet, no signing. It sends ONE unpaid request
per wall, base64-decodes the HTTP 402 `payment-required` header, parses the
x402 v2 envelope, and checks:

- `accepts[0].payTo` == canonical `0x9b8a27e03ceba490953cda8ab1291c0e13baf72f`
  (FULL 42-char case-insensitive compare — poison homoglyph-safe)
- `scheme` == `exact`
- `network` == `eip155:8453`
- `amount` > 0 (price path is `accepts[0].amount`, NOT `maxAmountRequired`)

Exit codes: `0` = every decoded wall canonical; `1` = drift detected;
`2` = no wall could be decoded (transport outage, not a trust failure).

## Output shape

```json
{
  "tool": "raen-fleet-price-oracle",
  "generated_at": "<UTC ISO-8601>",
  "source": "live HTTP 402 payment-required header, base64-decoded (x402 v2)",
  "canonical_payto": "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f",
  "walls_probed": 9,
  "walls_decoded": 6,
  "drift_count": 0,
  "walls": [ { "service": "...", "http": 402, "amount_atomic": 5000,
               "amount_usd": 0.005, "network": "eip155:8453",
               "scheme": "exact", "payto_canonical": true, "note": "OK" } ]
}
```

`registry/fleet-price-sheet.json` is a *snapshot* with a `generated_at` stamp.
Treat it as a cache, not an oracle: re-run the script for a fresh read. The
live challenge always wins over this file, the manifest, and any marketplace
listing.

## Buyer's rule

1. Fetch `registry/fleet-price-sheet.json` for a map of the fleet.
2. Re-run this script (or Recipe 23 on your target wall) immediately before paying.
3. Build an EIP-3009 `transferWithAuthorization` for `amount` atomic USDC on Base.
4. Retry the identical request with the signed envelope in **X-PAYMENT**
   (`PAYMENT-SIGNATURE` gets a silent re-challenge).
5. Verify settlement as a USDC Transfer to canonical payTo on Base.

## Honest notes

- Frozen/suspended services return 404, not 402 — the script records that
  honestly as `no 402 challenge`; absence is not a breach.
- Ladder prices land service-by-service. When a doc says "rolling out", the
  live 402 is authoritative. Verified live 2026-11-25: contract-eye $0.005
  and dispute-forge $0.01 ladder prices ARE serving; royal-ruby law-lookup
  still serves the pre-ladder $0.05; gateway $0.05; nanobanana $0.01.
- Read-only by construction: no code path signs a payment or moves funds.
