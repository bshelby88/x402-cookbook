# Recipe 31 — Catalog parity audit (find live walls the catalog forgot)

**Audience:** autonomous machine buyers and fleet operators.
**Cost:** free — unauthenticated GETs to `/health`, `/.well-known/x402.json`, and `/catalog.json`. No signing, no `X-PAYMENT`, no money movement.

## Why this exists

Machine buyers discover the RAEN fleet through `https://rae-fleet-router.fly.dev/catalog.json`. If a wall is live and canonical but missing from that catalog, the buyer cannot find it — no amount of buyer-side skill fixes a seller-side discovery gap. Recipe 23 (`buyer-preflight`) checks a URL you already know; recipe 29 (`bazaar-readiness`) grades a wall's metadata; recipe 30 (`intent-match`) ranks endpoints for an intent. **This recipe checks the catalog itself for completeness** before any of those tools are trusted.

## Run it

```bash
python scripts/catalog-parity.py
python scripts/catalog-parity.py --expected registry/known-live-walls.json --out report.json
python scripts/catalog-parity.py --fail-on-gap   # CI: exit 1 on a real gap or canonical drift
```

No third-party packages — Python stdlib only. Works on Windows and Linux.

## What it reports

| Field | Meaning |
|---|---|
| `discovery_gaps[]` | Host is live (`/health` 200) AND its manifest advertises the canonical `payTo`, but the host is absent from `/catalog.json`. This is the actionable defect. |
| `catalog_drift[]` | Catalog item has a non-canonical `payTo` or wrong network. Free routes with a null `payTo` are labeled `free_route_null_payto` and are **not** money misrouting — do not "fix" them by inventing a payee. |
| `unverifiable[]` | Expected host could not be probed this run (DNS/TLS/timeout). Partial coverage is stated, never silently treated as clean. |
| `coverage_pct` | Share of expected hosts actually advertised by the catalog. |

Truth order is unchanged: **live 402 challenge > live manifest > catalog > registry**. The expected-host registry only says where to look; the tool re-probes live health and manifest before calling an absence a gap.

## Interpreting a gap

A `discovery_gap` means the wall is buyable but undiscoverable through the main catalog — hand it to the fleet's router owner with the evidence block. It does **not** mean the wall is broken. Conversely, absence from the catalog does not make a wall illegitimate: use recipe 23 (`buyer-preflight`) on the direct host to verify its live 402 before paying.

## Shipped-state evidence (2026-11-25 run)

`registry/catalog-parity-20261125.json` is the verbatim output of the run that accompanied this recipe:

- catalog `generated_utc` 2026-11-25T23:13:27Z — 13 walls / 44 endpoints / 12 distinct hosts
- expected 13 hosts, `coverage_pct` 92.3, zero unverifiable
- **1 discovery gap:** `contract-eye-x402.fly.dev` — health 200, manifest payTo `0x9b8a27e03CEbA490953cDa8AB1291c0E13bAf72f` (canonical, mixed case), absent from the catalog. Corroborated independently by Library artifacts `e42ff3a8` (TIFFANY EXEC) and `b36a808e` (BEAN RUN).
- 6 `free_route_null_payto` entries (1 power-pack unreachable + 5 royal-ruby free wrong-network routes) — explicitly NOT drift.

After the router owner adds the missing host, re-run the tool: the gap must disappear and `coverage_pct` should reach 100. Until then, machine buyers can still reach the wall directly with recipe 08 (`contract-eye`) + recipe 23 (`buyer-preflight`).
