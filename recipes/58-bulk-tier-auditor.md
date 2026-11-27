# 58. Volume-Tier Truth Auditor — does the bulk price survive contact with the live 402?

Tools 23 (buyer preflight), 24 (price oracle) and 46 (budget guard) all read the
BASE 402. But the owner's KPI is **calls per payer** — an autonomous buyer that
scales up is exactly the buyer who needs the advertised volume discount to be
real. This tool closes that gap: it probes each paid wall at the base call and at
every documented bulk quantity and grades the ladder, read-only.

## Runs
```bash
python3 scripts/bulk-tier-auditor.py
python3 scripts/bulk-tier-auditor.py --check        # CI gate: HARD drift only
python3 scripts/bulk-tier-auditor.py --out snap.json
```

## What it checks
1. **Manifest truth** — parse the wall's OWN `/.well-known/x402.json` for volume
   claims (`$0.002/citation for 10-99`) and base claims (`$0.05 per call`).
2. **Live ladder** — unpaid POST at base + each quantity (5/9/10/50/100/500 for
   royal-ruby), decode `payment-required`, read `accepts[0].amount`.
3. **Canonical envelope on every tier** — `exact` / `eip155:8453` / full canonical
   payTo / canonical USDC asset / integer amount.
4. **Floor + monotonicity** — below the documented minimum is the base price;
   a larger tier never costs more per unit than a smaller one or than base.
5. **Advertised vs live** — manifest tiers are the seller's promise; a cookbook
   tier with no manifest/live support is a `DOC_DRIFT` finding (never blamed on
   the service), with the over-budget multiplier stated explicitly.

## Honest output — 2026-11-27 17:2xZ
Verdict `DOC_DRIFT_WARN`, zero hard drift. royal-ruby's ladder is genuine and
canonical (floor + both price bands verified live). contract-eye and nanobanana
advertise bulk in the cookbook only — the live 402s stay flat at base. A buyer
budgeting 100 contract analyses from the cookbook would budget $0.10 and be
charged $0.50. royal-ruby's manifest also carries a stale $0.05 base (live $0.005).

Snapshot `registry/bulk-tier-auditor.json`; buyer card `registry/bulk-tier-auditor.md`.

## Refusal guards
No signing key, no X-PAYMENT header, no on-chain writes, no deploy, no external
sends. All probes are unpaid POSTs that can only return a 402 — no paid output is
collected. Prices and docs are owner-gated: this tool REPORTS drift, never edits a
price or a manifest. `--check` fails only on hard drift, never on doc drift.
