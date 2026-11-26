# Machine-buyer trust coverage — independent verification, honest gaps

Generated 2026-11-26T11:09:58.705817Z by `trust-coverage/1.0`. Every verdict below is a LIVE read from Lumi's public trust-check API keyed by URL, plus a canonical-payTo guard from a fresh unpaid 402 on the kept-live walls. No cached or hand-typed verdicts. Guard verdict: **CLEAN**.

## What an independent trust layer currently says about RAEN

| Surface | Role | Lumi label | Observed? | Test buys |
|---|---|---|---|---|
| royal-ruby | kept-live | `check_first` | yes | 0 |
| contract-eye | kept-live | `check_first` | yes | 0 |
| nanobanana | kept-live | `check_first` | yes | 0 |
| sentry-forge | kept-live | `no_data` | no | 0 |
| raen-mcp-gateway | kept-live | `no_data` | no | 0 |
| raen-mcp-gateway/mcp | kept-live | `no_data` | no | 0 |
| settlement-collector | infra | `no_data` | no | 0 |
| raen-blog | infra | `no_data` | no | 0 |
| escrow | frozen-public | `check_first` | yes | 0 |
| dispute-forge | frozen-public | `check_first` | yes | 0 |
| briefsnap | frozen-public | `check_first` | yes | 0 |
| vault-pro | frozen-public | `check_first` | yes | 0 |
| dispatch | frozen-public | `check_first` | yes | 0 |
| nft-alpha | frozen-public | `check_first` | yes | 0 |

**Reading this table:** `no_data` / `not_observed` means Lumi has no record — not a negative finding. `check_first` means Lumi knows the URL but has not test-bought it. None of these URLs has a third-party test-buy record, so no independent delivery proof exists yet. That is a discovery GAP we publish rather than hide.

## Canonical payTo guard (fresh unpaid 402 challenges)

| Wall | HTTP | network | scheme | payTo canonical? |
|---|---|---|---|---|
| royal-ruby | 402 | `eip155:8453` | `exact` | YES |
| contract-eye | 402 | `eip155:8453` | `exact` | YES |
| gateway | 402 | `eip155:8453` | `exact` | YES |

## Verify RAEN yourself (no account, no key)

```bash
# 1. Ask the independent trust layer (URL-encoded):
curl -sG --data-urlencode "url=https://raen-mcp-gateway.fly.dev/mcp" \
  https://api.lumitrades.io/v1/trust/check

# 2. Decode a live 402 yourself — compare payTo to the canonical address:
curl -s -D - -o /dev/null -X POST https://contract-eye-x402.fly.dev/api/analyze-contract \
  -H "Content-Type: application/json" -d '{"text":"test","focus":["renewal"]}'

# 3. Prove settlement on-chain, not from our dashboard (recipe 27):
npx -y tsx scripts/buyer-receipt.ts <YOUR_TX_HASH>
```

## Honesty

- A Lumi 'no_data' verdict means NOT OBSERVED, not negative — Lumi has no record of the seller.
- Absence from a trust catalog is a discovery GAP; it is not proof of fraud or non-delivery.
- Lumi never test-bought these URLs (test_buys=0); paying for a high-value check does not change the verdict.
- A 402 challenge is a demand signal, not a sale. Fleet external revenue is $0.00 unless the chain says otherwise.
- Internal AgentCash self-pays are not external revenue. Verification is independent of our own dashboards.
- Claiming / monitoring a third-party trust listing is an owner-lane action; this report only measures it.

This report does not claim a sale. Machine-buyer acquisition, not cold outreach, is the priority; trust friction is one measurable part of it.
