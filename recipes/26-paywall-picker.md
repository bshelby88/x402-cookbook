---
permalink: /recipes/26-paywall-picker.md
---

# Recipe 26 — Pick My Paywall (live-grounded recommender for machine buyers)

**Innovation 2026-11-25 (Tiffany, machine-buyer acquisition).** Recipe 23 verifies
*one* wall before you sign; recipe 24 publishes the price of *every* wall. Neither
answers the question a new agent actually has: **which of the 37 pay links should I
call first?** A buyer that lands on the catalog and has to choose among dozens of
slugs stalls before the first dollar moves. This recipe ships a deterministic,
zero-cost picker that turns three answers into one primary pay link plus up to two
alternates — grounded entirely in a fresh read of the live catalog.

## The truth it uses

- Source of truth is `GET https://rae-fleet-router.fly.dev/buy?format=json`, not a
  hand-maintained table. Prices, endpoints, methods and `amount_micro` are read
  from that snapshot at run time; the script never hardcodes a price or invents a slug.
- Only items with `status == "ok"`, a positive numeric `price_usdc`, and a **full
  42-character case-insensitive match** to canonical `payTo`
  `0x9b8a27e03ceba490953cda8ab1291c0e13baf72f` are eligible. Homoglyph addresses
  cannot slip through a `startswith` check.
- Everything excluded is named in the output with its reason — the 2026-11-25
  snapshot had 37 items but only 30 healthy priced ones. Seven were excluded:
  `power-pack` (unreachable), `royal-ruby` (no positive price), and five
  `wrong_network` entries. TRUTH law: a picker that silently advertised a broken
  wall would cost a buyer more than no picker at all.

## Run it

```bash
# one recommendation
python3 scripts/paywall-picker.py --need image --budget penny --urgency quick

# regenerate the whole 36-leaf decision tree from a fresh live snapshot
python3 scripts/paywall-picker.py \
  --generate-pack registry/paywall-picker.json \
  --save-snapshot plan-78-buysnapshot.json

# fail if the shipped pack has drifted from the live catalog
python3 scripts/paywall-picker.py --verify-pack registry/paywall-picker.json
```

Stdlib only. **Read-only: no signing, no wallet, no payment header, no funds moved.**
Exit 0 = OK/PASS, 1 = drift or bad contract, 2 = transport failure.

## Live-verified 2026-11-25

- Pack generated from snapshot `2026-11-25T18:18:15.971Z`: **37 catalog items,
  30 healthy priced, 36 decision leaves** (6 needs × 3 budgets × 2 urgencies).
- `image / penny / quick` → `nanobanana` at `0.01` USDC
  (`/api/generate-image`, `10000` atomic), alternate `nanobanana__edit-image`.
- `data / penny / quick` → `nft-alpha` at `0.005`, alternates `suprapack`,
  `suprapack__get-skill`.
- `--verify-pack` against the exact saved snapshot: **36 leaves checked, 0 drift,
  verdict PASS.**
- `registry/paywall-picker.json` carries the three questions, all 36 leaves, the
  exclusion list, and a JSON Schema for a `/recommend.json` response so a
  buying agent can validate the result before acting on it.

## Why it helps acquisition

The first machine-buyer failure is not service quality — it is an unanswered
"what do I call?" across a large catalog. Recipe 23 protects the last step before
signing and recipe 24 publishes prices; this one closes the *first* step. Together
they make discovery → selection → preflight → first settled call a path a machine
can take without a human in the loop. The router is read-only here: the picker
never deploys, restarts or changes a wall, so it is safe under a burn freeze.
