# x402 Playground — verified walkthrough content pack (Recipe 37)

**Status:** DRIFT · generated 2026-11-26T06:30:09.119132+00:00
**Playground:** https://rae-fleet-router.fly.dev/playground (HTTP 200)

This pack turns the /playground into a trustworthy *machine-buyer* asset. It
re-probes kept-live walls with unpaid POSTs and uses ONLY the live 402 price.

## Truth rules (read first)

- Price truth = a fresh live 402 challenge (accepts[0].amount), never the hardcoded playground price.
- Many 402 challenges are scanners/bots; challenges are not sales. See Recipe 36.
- Internal self-pays (AgentCash) are not external revenue.
- Frozen walls are labelled NOT VERIFIED and are never probed (BURN FREEZE).
- Chain-coverage: this verifies Base (eip155:8453) only - the chain RAEN walls settle on.

Canonical payTo (full 42 chars): `0x9b8a27e03ceba490953cda8ab1291c0e13baf72f`
Chain `eip155:8453` · scheme `exact`

## Verified walls (fresh unpaid 402 decode)

| wall | HTTP | live price | payTo role | network | scheme |
|------|------|-----------:|------------|---------|--------|
| royal-ruby | 402 | $0.05 | CANONICAL | eip155:8453 | exact |
| contract-eye | 402 | $0.005 | CANONICAL | eip155:8453 | exact |
| gateway | 402 | $0.05 | CANONICAL | eip155:8453 | exact |

## Advertised playground walls vs live truth

| advertised wall | advertised | live | status |
|-----------------|-----------:|-----:|--------|
| rae-fleet-router /api/fleet-bundle | $0.07 | not probed | NOT VERIFIED (frozen) |
| rae-fleet-router /api/bundle/market-starter | $0.02 | not probed | NOT VERIFIED (frozen) |
| rae-fleet-router /api/bundle/market-intel-trio | $0.05 | not probed | NOT VERIFIED (frozen) |
| rae-fleet-router /api/bundle/full-fleet-sampler | $0.06 | not probed | NOT VERIFIED (frozen) |
| dispatch-x402 /dispatch | $0.5 | not probed | NOT VERIFIED (frozen) |
| dispute-forge-x402 /api/dispute-pack | $0.75 | not probed | NOT VERIFIED (frozen) |
| escrow-x402 /api/escrow/create | $0.05 | not probed | NOT VERIFIED (frozen) |
| nft-alpha-x402 /api/nft-signal | $0.02 | not probed | NOT VERIFIED (frozen) |
| power-pack-x402 /api/score-email | $0.01 | not probed | NOT VERIFIED (frozen) |
| royal-feel-x402 /api/lint-copy | $2 | not probed | NOT VERIFIED (frozen) |
| royal-feel-x402 /copy/lint | $2 | not probed | NOT VERIFIED (frozen) |
| royal-feel-x402 /api/batch-lint | $5 | not probed | NOT VERIFIED (frozen) |
| royal-ruby-x402 /api/law-lookup | $0.25 | $0.05 | VERIFIED ⚠️ DRIFT |
| suprapack-x402 /api/find-skill | $0.03 | not probed | NOT VERIFIED (frozen) |
| suprapack-x402 /api/get-skill | $0.03 | not probed | NOT VERIFIED (frozen) |
| suprapack-x402 /api/list-top | $0.03 | not probed | NOT VERIFIED (frozen) |
| tradingagents-x402 /api/analyze-arbitrage | $0.05 | not probed | NOT VERIFIED (frozen) |
| tradingagents-x402 /api/analyze-ticker | $0.05 | not probed | NOT VERIFIED (frozen) |
| vault-pro-x402 /api/scaffold-project | $0.05 | not probed | NOT VERIFIED (frozen) |
| vault-pro-x402 /api/scaffold-agent | $0.05 | not probed | NOT VERIFIED (frozen) |
| raen-portfolio-x402 /api/portfolio | $0.01 | not probed | NOT VERIFIED (frozen) |

Price-drift walls: **1**

## Walkthrough a machine buyer can follow

1. **Preflight** (free): `python3 scripts/buyer-preflight.py` — verify the wall before you sign (Recipe 23).
2. **Unpaid POST** to the wall → HTTP 402. Decode `payment-required` (base64 JSON); `accepts[0]` is authoritative.
3. **Build the payment** for `accepts[0].amount` (micro-USDC) to the canonical payTo above on `eip155:8453`, scheme `exact` (EIP-3009 `transferWithAuthorization`).
4. **Retry the POST** with the `X-PAYMENT` header. Never reuse a signature.
5. **Prove it landed**: `python3 scripts/receipt-verifier.py <tx>` — chain truth, no seller trust (Recipe 27).

For a first paid call, use a wall marked VERIFIED above at its **live** price —
not a frozen wall and not a stale advertised price.
