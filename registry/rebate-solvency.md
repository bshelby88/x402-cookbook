# Buyer card — Rebate Promise Solvency (tool 67)

**Live check: 2026-11-28 03:5xZ — PASS / SOLVENT.**

You were told royal-ruby's first call is free: pay the normal $0.005 challenge, send `x-payer-address: <your 0x address>`, and the rebater returns $0.005 USDC after settlement — net cost $0, once per wallet per 30 days.

We checked whether that promise can actually be kept:

- **Promise advertised:** yes — in both the public manifest and OpenAPI.
- **Live price it will charge:** $0.005 (x402 v2, `exact`, `eip155:8453`, canonical `payTo`), matching the advertised $0.005 rebate.
- **Rebater rail:** enabled (`royal-ruby-rebater.fly.dev/health`), daily cap 100.
- **Treasury:** `0xfBC0eb7811D477E55261d956dF39f0046E192240` — a full-form, known internal RAEN wallet (AgentCash), not a lookalike.
- **Funds on Base:** 11.515259 USDC + 0.0017 ETH gas, agreed by 3 independent RPCs with `chainId 0x2105` validated.
- **Coverage:** ~2,303 rebates at $0.005. The 100/day cap is $0.50/day — well inside the float.

**Verdict:** the "net cost $0" hook is real and fundable. Paying the $0.005 challenge and sending `x-payer-address` is expected to return the rebate. Full-form address discipline: never send your rebate address to a truncated or lookalike `0xfbc0…` string.

This card is a timestamped snapshot. Re-run `scripts/rebate-solvency.py` before relying on it — the chain is the truth, not this file.
