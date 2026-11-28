# 65. x402 Challenge Determinism Auditor

**Goal:** prove the same unpaid probe returns the same canonical 402 every time — because a machine buyer's preflight and budget policy break silently when two identical requests disagree.

## Why this exists (acquired-data comparison first)
Every prior tool grades ONE 402 snapshot. But RAEN's own ops history is full of concurrent deploys, stale images, live-only machine-side changes and GHCR/Actions races that can leave machines serving different challenges (documented in the steward doctrine: `deploy` can pull a stale GHCR image, live-only reprices get reverted, a stale clone silently drops features). Other tools cannot see that: 24/61 grade a single price against the winner band, 42 compares GET vs HEAD vs POST, 57 grades MCP bridge prices, 58 grades volume tiers across quantities, 62 grades single-probe constructability + header/body agreement, 64 grades point-of-sale offer disclosure. **None repeats an identical unpaid probe to test temporal determinism.** That gap is this tool.

## What it does
Read-only, stdlib-only. For each of 8 kept-live paid surfaces (3 walls + 5 MCP gateway paid tools):

1. Send the SAME unpaid `POST` three times (no `X-PAYMENT`, no key, 1s apart).
2. Decode each live 402 (`payment-required` header or SSE body `accepts[]`).
3. Build a fingerprint of the canonical payment envelope: `scheme`, `network`, `payTo`, `asset`, `amount`, `maxTimeoutSeconds`, EIP-3009 `extra.name`/`extra.version`, and `resource`.
4. Grade: `STABLE` (all three identical and canonical), `UNSTABLE` (a named field drifts between probes), `DRIFT` (a hard canonical defect or free backdoor), `NO_CHALLENGE`.
5. Aggregate a fleet determinism score and name any unstable/blocked targets.

`--check` fails on hard drift or instability, NEVER on a price being outside the owner-gated band. Pricing is owner-gated; this tool never reprices, deploys, signs, pays, or moves funds.

## Run
```bash
python3 scripts/determinism.py
python3 scripts/determinism.py --json      # registry/determinism.json
python3 scripts/determinism.py --self-test
python3 scripts/determinism.py --check     # exit 1 on hard drift/instability only
```

## Live result — 2026-11-28 01:40Z
`8/8 STABLE, 100.0% determinism, verdict DETERMINISTIC, 0 hard drift, 0 unstable targets`.

| Surface | Price | 3x probes |
|---|---|---|
| royal-ruby `/api/law-lookup` | $0.005 | STABLE |
| contract-eye `/api/analyze-contract` | $0.005 | STABLE |
| nanobanana `/api/generate-image` | $0.010 | STABLE |
| gateway `raen_law_lookup` | $0.005 | STABLE |
| gateway `raen_ticker_analysis` | $0.001 | STABLE |
| gateway `raen_dispute_letter` | $0.010 | STABLE |
| gateway `raen_image_generate` | $0.010 | STABLE |
| gateway `raen_contract_analysis` | $0.005 | STABLE |

No price, payTo, network, scheme, asset, timeout, EIP-3009 domain or resource drift across any target. This is positive evidence against stale-machine / stale-image drift on the kept-live paid path right now — the first tool to check that axis rather than assume it.

**Handoff:** none blocking. If `--check` later fails on `UNSTABLE`, diff the affected app's live machines before redeploying (stale image / live-only change), under the owner's burn-freeze rules. Self-test 5/5 PASS; `py_compile` OK; live `--check` exit 0.

Snapshot: `registry/determinism.json` + buyer card `registry/determinism.md`. Read-only, stdlib-only, no signing, no X-PAYMENT, no price change, no deploy.

> Correction note: this slot was first drafted as a price-band auditor, which duplicated tool 61 (`recipes/61-price-band-auditor.md`, `scripts/price-band.py`). Acquired-data comparison caught it before final publication; the band auditor remains tool 61 and this slot is the determinism tool. `recipes/65-price-band.md` is a redirect stub pointing here.
