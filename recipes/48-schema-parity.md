# Recipe 48 — x402 Buyer Schema Parity Auditor

**Status:** read-only, stdlib-only, no signing, no payment, no deploy.
**Script:** `scripts/schema-parity.py`
**Live snapshot:** `registry/schema-parity.json`

## The gap this closes

A machine buyer generates its request from two free surfaces: the seller's
`/.well-known/x402.json` (which advertises what to POST) and `/openapi.json`
(which a code generator reads for request fields). When those two disagree, the
buyer builds a wrong body and **never reaches the price** — the exact
schema-drift failure mode in the RAEN steward doctrine ("published docs that
name a field the route rejects kill the buyer before they ever see a price").

This tool compares the two surfaces across the kept-live walls and reports, in
machine-readable form, which fields the manifest advertises but OpenAPI does
not declare. It never probes a paid route, never attaches `X-PAYMENT`, and
never moves money.

## Truth order

Live manifest + live OpenAPI (both free) > generated client. A stale generated
client is the bug, not the live surface.

## What it checks

- **Paid routes only.** GET/free discovery/preview routes (ping, llms.txt,
  agent-card, openapi.json) are skipped and counted, never flagged.
- **Request fields, not response shapes.** Only brace lists introduced by a
  POST/send/body/request clause count; `returns {status, latency_ms, ...}`
  is ignored. Nested objects collapse to their top-level key
  (`expect?: {amountAtoms, ...}` -> `expect`).
- **Canonical payTo guard** on every paid resource (full 42-char address,
  case-insensitive).
- **Verdict per route:** `PASS`, `DRIFT` (advertised field absent from OpenAPI
  schema), or `PAYTO_DRIFT`.

## Usage

```bash
python3 scripts/schema-parity.py                         # print findings
python3 scripts/schema-parity.py --out registry/schema-parity.json
python3 scripts/schema-parity.py --check                 # exit 1 on drift (CI)
```

Exit: `0` clean, `1` drift on a paid wall, `2` fetch failure.

## Live result (2026-11-27, this run)

- royal-ruby: `/api/law-lookup` PASS (OpenAPI declares `topic`, `state`,
  `scope`); `/api/validate-json` PASS. 7 free routes skipped.
- nanobanana: `/api/generate-image` + `/api/edit-image` PASS (OpenAPI declares
  `prompt`, `aspectRatio`, `image_b64`, `mime_type`).
- raen-mcp-gateway: `/mcp` PASS (no request-field contract advertised; 5 free
  routes skipped).
- **contract-eye DRIFT (3 routes):** manifest advertises `{text, focus?}` but
  OpenAPI declares no `requestBody` schema on `/api/analyze-contract`,
  `/contract/analyze`, or `/api/analyze`. An agent generating a client from
  OpenAPI cannot learn that the route needs `text`.
- **shipgate402 DRIFT (2 routes):** manifest advertises `{url, expect?, probe?}`
  (`/v1/ship-check`) and `{urls, expect?, probe?}` (`/v1/ship-check/batch`) but
  OpenAPI declares no `requestBody` schema on either.

All 5 walls fetched clean (0 fetch errors). These are documentation defects,
not paywall breaks: the live paid POST routes remain canonical on every wall.

## Handoff

- `[staci]` / `[kip]`: add `requestBody` schemas to contract-eye and
  shipgate402 OpenAPI (paid POST paths) so generated clients carry the
  advertised fields. Deploy-lane work, owner freeze honored (read-only here).
- `[tiffany]` (self): re-run after the OpenAPI fix; `--check` should return 0.

Read-only. No signing, no X-PAYMENT, no deploy, no funds moved.
