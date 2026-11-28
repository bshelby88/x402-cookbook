# 65. Machine-Buyer Price-Band Conformance Auditor

**Goal:** grade every live RAEN entry price against the only cohort that actually wins machine buyers — and hand the owner a decision sheet for the open band item, without ever changing a price.

## Why this exists (acquired-data comparison first)
The consolidated world-revenue audit (2026-11-26) verified that the only true machine-buyer winners sell per-call consumables in the **$0.003–$0.01 band** (twit.sh $0.006/call, 120 buyers, $621/30d; BlockRun ~$177K/30d). Across the full Bazaar sweep (88,788 resources, 3.93M paid calls) the paid-call price p25/median/p75 is **$0.003/$0.003/$0.005**. The audit also named a **dead zone** ($0.01–$0.50: above machine willingness-to-pay, below human WTP) and human-paid tiers (≥$0.50). RAEN's Airtable item **TIFF-BUYER-BAND-01** ("price an entry ticket inside the band the only real machine buyer actually spends") is still open and owner-gated.

Tools 24 (price oracle) and 62 (constructability) report raw prices or emit a binary below/above warn; 46 (budget guard) tests affordability; 58 (volume tier) grades bulk ladders. **None grades the live entry price against the acquired-world band with a dead-zone/human-tier distinction, aggregates fleet band health, or emits a decision artifact for the open band item.** That gap is this tool.

## What it does
Read-only, stdlib-only. For each kept-live paid wall plus the MCP gateway's five paid tools:

1. Unpaid `POST` (no `X-PAYMENT`, no key) to force the live 402 challenge.
2. Decode `payment-required` (base64) or the SSE body `accepts[]`; read `accepts[0].amount` in atomic units and convert at 6 decimals.
3. Enforce HARD gates only on the canonical envelope: `scheme=exact`, `network=eip155:8453`, full 42-char canonical `payTo`, canonical Base USDC `asset`, header/body agreement. A 200 on a paid call is a `DRIFT` (free backdoor).
4. Classify the price against the acquired band:
   - `IN_BAND` — $0.003–$0.01 (winner cohort)
   - `BELOW_FLOOR` — < $0.003 (below verified machine floor; signal-value risk)
   - `DEAD_ZONE` — $0.01–$0.50 (above machine WTP, below human)
   - `HUMAN_TIER` — ≥ $0.50 (human-paid, not machine demand)
5. Aggregate a fleet band distribution, in-band share, and a `BAND_CONFORMANT`/`BAND_GAPS` verdict, with the acquired benchmark and the open owner item embedded.

A band verdict is an **owner-gated WARN**, never a hard failure. Pricing is owner-gated; this tool never reprices, deploys, signs, pays, or moves funds.

## Run
```bash
python3 scripts/price-band.py            # human report
python3 scripts/price-band.py --json     # full snapshot (registry/price-band.json)
python3 scripts/price-band.py --self-test
python3 scripts/price-band.py --check    # exit 1 on HARD drift only, never on a band verdict
```

## Live result — 2026-11-28 01:30Z
`8/8 CANONICAL, 0 hard defects, band_verdict=BAND_GAPS, in_band=87.5%`.

| Wall | Price | Band |
|---|---|---|
| royal-ruby `/api/law-lookup` | $0.005 | IN_BAND |
| contract-eye `/api/analyze-contract` | $0.005 | IN_BAND |
| nanobanana `/api/generate-image` | $0.010 | IN_BAND |
| gateway `raen_law_lookup` | $0.005 | IN_BAND |
| gateway `raen_ticker_analysis` | $0.001 | **BELOW_FLOOR** |
| gateway `raen_dispute_letter` | $0.010 | IN_BAND |
| gateway `raen_image_gen` | $0.005 | IN_BAND |
| gateway `raen_contract_review` | $0.005 | IN_BAND |

Distribution: `IN_BAND 7, BELOW_FLOOR 1, DEAD_ZONE 0, HUMAN_TIER 0, UNPRICED 0`. The whole kept-live fleet sits inside the acquired winner band except `raen_ticker_analysis` at $0.001 — the already-known owner-gated price drift (tools 57/62). No dead-zone or human-tier walls remain among kept-live apps (those are the frozen apps: dispatch $0.50, sentry-forge $5, briefsnap $1–3 — untouched under burn freeze).

**Handoff (owner-gated):** band item TIFF-BUYER-BAND-01 can be closed as "kept-live entry prices already conform to the verified $0.003–$0.01 machine band; sole outlier is ticker $0.001, raise to ≥$0.003 to clear the floor." This tool reports; it does not reprice. `--check` exits 0 (no hard drift).

Snapshot: `registry/price-band.json` + buyer card `registry/price-band.md`. Read-only, stdlib-only, no signing, no X-PAYMENT, no price change, no deploy.
