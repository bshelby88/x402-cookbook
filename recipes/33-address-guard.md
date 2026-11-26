---
permalink: /recipes/33-address-guard.md
---

# Recipe 33 — Canonical address guard: catch retired payees and poison homoglyphs

**Innovation 2026-11-25 (Tiffany, machine-buyer acquisition).** Recipe 23 preflights one wall's live challenge, recipe 27 proves a settlement on-chain, and recipe 32 audits buyer docs — but none of them answers the cheapest, most catastrophic question: *"is every `0x…` address I just read actually the one RAEN pays to?"* The treasury address is normally quoted by prefix/suffix (`0x9b8a…f72f`), and **poison homoglyphs exist** — a one-character edit that passes a prefix/suffix check and silently misroutes money. This ships a zero-cost, read-only guard that classifies every 42-character address in any text against the known RAEN roles and flags near-matches.

The script: [`scripts/address-guard.py`](../scripts/address-guard.py) (Python 3 stdlib only; no dependencies, no signing, no RPC money calls, no funds movement, no external sends).

## Why this exists

Real incidents on this fleet, all caused by address shorthand or lookalikes:

- A Nov-21 wallet census used shorthand `0xfbc0…2240` and hit a homoglyph (`0xfbc04a6b…42240`), reporting **0.0 on both chains** while the real AgentCash wallet held 20.5 USDC. The fix was to always grep the **full 42-character address** from `ops/SYNCED-MEMORY-STATE`.
- The treasury has a **RETIRED** address (`0x7861db4efc14a1ed5dd8c96c528a3796560f1393`). Older docs and Bazaar/Lumi records still carry it. Paying it is a total loss.
- Live buyer docs legitimately *name* the retired address as a reject example (`/pay-failed?format=json`). A guard must flag it for a buyer while an auditor's context guard may suppress it — context is the caller's job, classification is the tool's.

## Known roles (full, case-insensitive)

| Role | Address | Meaning |
|------|---------|---------|
| CANONICAL | `0x9b8a27e03ceba490953cda8ab1291c0e13baf72f` | pay here |
| RETIRED | `0x7861db4efc14a1ed5dd8c96c528a3796560f1393` | never pay |
| AGENTCASH | `0xfbc0eb7811d477e55261d956df39f0046e192240` | internal funding wallet, not a seller |

Any address within **Hamming distance ≤2** of a role but not equal is flagged `POISON_SUSPECT` with its nearest role. Everything else is `UNKNOWN` (e.g. the USDC token contract `0x833589fC…A02913`, which is a token address, not a payment target).

## Run it (costs nothing)

```bash
# Scan a live doc, a local file, or stdin
python3 scripts/address-guard.py https://royal-ruby-x402.fly.dev/pricing.md
python3 scripts/address-guard.py recipes/20-royal-ruby-ping.md
echo "$CHALLENGE_JSON" | python3 scripts/address-guard.py -

# Machine-readable; exit 1 on RETIRED or POISON_SUSPECT (safe for CI / pre-pay gates)
python3 scripts/address-guard.py --url https://host/llms.txt --json

# Auditing a reject-list that intentionally contains the retired address: don't fail
python3 scripts/address-guard.py --url 'https://host/pay-failed?format=json' --no-fail
```

Exit codes: `0` = clean / no addresses / `--no-fail`; `1` = at least one RETIRED or POISON_SUSPECT found (the default, so an agent can hard-block before spending).

## Real verified output (2026-11-25, live)

Synthetic stress case — canonical, retired, a 1-char canonical homoglyph, a 1-char AgentCash homoglyph, and an unrelated address:

```
address-guard: 5 address(es) across 1 source(s)
  CANONICAL      0x9b8a27e03ceba490953cda8ab1291c0e13baf72f  stdin
  RETIRED        0x7861db4efc14a1ed5dd8c96c528a3796560f1393  stdin
  POISON_SUSPECT 0x9b8a27e03ceba490953cda8ab1291c0e13baf72e  stdin
      -> {"nearest": "CANONICAL", "hamming_distance": 1}
  POISON_SUSPECT 0xfbc0eb7811d477e55261d956df39f0046e192241  stdin
      -> {"nearest": "AGENTCASH", "hamming_distance": 1}
  UNKNOWN        0x1111111111111111111111111111111111111111  stdin
      -> {"nearest_hamming": 36}
VERDICT: UNSAFE        (exit 1)
```

Live probes: `https://rae-fleet-router.fly.dev/pricing.md` → 2 addresses, one CANONICAL, `VERDICT: CLEAN`. `https://rae-fleet-router.fly.dev/pay-failed?format=json` → 3 addresses (USDC token = UNKNOWN, canonical, **RETIRED**), `VERDICT: UNSAFE` — correct: the retired address appears there as a reject example, and a buyer must never pay it.

## Truth constraints

- **Chain scope:** this tool classifies *addresses in text*; it does not read the chain. For on-chain settlement proof use [recipe 27](27-buyer-receipt.md). For live challenge verification use [recipe 23](23-buyer-preflight.md).
- Roles are pinned to `ops/SYNCED-MEMORY-STATE` full addresses; never edit them on prefix/suffix shorthand.
- External earned revenue to date is **$0.00** (chain truth). This tool is a buyer-safety surface, not a revenue claim.
- No post, no deploy, no external send is performed by this recipe.
