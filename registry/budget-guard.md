# RAEN Budget Guard - spend plan (2026-11-26 16:59:19Z)

- Budget: **$0.100000 USDC** (reserve 10% -> usable **$0.090000 USDC**)
- Verdict: **AFFORDABLE** | planned total **$0.070000** | drift 0/4
- Prices are LIVE-READ from unpaid 402 challenges; the live 402 is authoritative.
- Canonical payTo (full 42-char): `0x9b8a27e03ceba490953cda8ab1291c0e13baf72f`

| wall | live price | plan | planned cost | max calls in usable budget |
|---|---|---|---|---|
| royal-ruby | $0.005000 | 1 | $0.005000 | 17 |
| contract-eye | $0.005000 | 1 | $0.005000 | 17 |
| nanobanana | $0.010000 | 1 | $0.010000 | 8 |
| raen-mcp-gateway | $0.050000 | 1 | $0.050000 | 1 |

## Copy-ready agent budget policy
```json
{
  "currency": "USDC",
  "network": "eip155:8453",
  "payTo_allowlist": [
    "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f"
  ],
  "budget_usdc": 0.1,
  "usable_usdc": 0.09,
  "reserve_pct": 10,
  "max_per_call_usdc": {
    "royal-ruby": 0.005,
    "contract-eye": 0.005,
    "nanobanana": 0.01,
    "raen-mcp-gateway": 0.05
  },
  "require_canonical_payto": true,
  "on_challenge_drift": "ABSTAIN",
  "signing": "buyer-supplied wallet only"
}
```

This tool never signs or sends X-PAYMENT. It only reads live 402 challenges. Signing is the buyer's own wallet step.
