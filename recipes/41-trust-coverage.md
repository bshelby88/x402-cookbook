---
permalink: /recipes/41-trust-coverage.md
---

# Recipe 41 — Machine-buyer trust coverage: independent verification, honest gaps

**Status:** shipped 2026-11-26 (Tiffany, machine-buyer acquisition, closes Airtable `ERICA-LUMI-CATALOG-GAP`, P2). Free, read-only, stdlib-only. Third-party trust checks by URL + unpaid 402 canonical guard on kept-live walls. No signing, no `X-PAYMENT`, no funds movement, no external sends, no directory POSTs, no deploys, no secrets. BURN FREEZE: frozen services are never probed locally — Lumi checks are third-party calls by URL and do not touch them.

A machine buyer's last question before paying is *"can I verify this seller through an independent trust layer?"* Before this recipe the answer was unknowable: `ERICA-LUMI-CATALOG-GAP` recorded that Lumi returned `no_data` for the gateway and collector, and Lumiere PayCheck had them queued but `not_monitored`. Recipe 41 turns that open gap into a live, publishable coverage map instead of an assumption.

The script: [`scripts/trust-coverage.py`](../scripts/trust-coverage.py). Outputs: `registry/trust-coverage.json` (machine truth snapshot) and `registry/trust-coverage.md` (buyer-facing copy).

## What it does

For each of 14 public RAEN surfaces (6 kept-live, 2 infra, 6 frozen-public):

1. Calls Lumi's public `trust/check?url=` API and records the **live** verdict — `label`, `scope`, `test_buys`, `delivered`, `last_quote_check`, `as_of`. Read from the API, never hand-typed.
2. On the three kept-live walls only, sends one unpaid POST and decodes the base64 `payment-required` header — `accepts[0]` gives `payTo`, `network`, `scheme` for a canonical guard (full 42-char case-insensitive compare; `eip155:8453`; `exact`).
3. Emits a buyer-facing coverage table plus three copy-paste verification commands (Lumi check, live 402 decode, on-chain receipt via recipe 27) so a buyer can verify RAEN without an account or an API key.
4. Exit 0 CLEAN / 1 DRIFT / 2 UNREACHABLE — CI-safe, drift-failing.

## Verified 2026-11-26

Guard **CLEAN** — 3/3 kept-live walls returned a live 402 with full canonical payTo, `eip155:8453`, `exact`, 0 drift: royal-ruby `/api/law-lookup` $0.05, contract-eye `/api/analyze-contract` $0.005, gateway `/mcp` tools/call $0.05. `py_compile` OK.

Trust coverage across 14 surfaces: **9 `check_first`, 5 `no_data`, 0 verified** — `test_buys = 0` on every URL. That is the honest finding: **no independent third-party test-buy proof exists for any RAEN surface.** `no_data` means "not observed," not a negative finding; `check_first` means Lumi knows the URL but has not bought it. Both are discovery GAPS, published rather than hidden.

## The gap this closes

`ERICA-LUMI-CATALOG-GAP` (open, P2): Lumi returned `no_data` for the gateway and collector; Lumiere PayCheck had them `not_monitored`. This recipe (a) re-verifies that live, (b) generalizes it to all public surfaces with a reproducible script, and (c) gives machine buyers a self-serve verification path. Claiming or paying for a third-party trust listing is owner-lane — this asset measures the gap, it does not spend or sign anything.

## Honesty

- A `no_data` trust verdict is absence of evidence, not evidence of absence — it is not a fraud signal.
- A 402 is a demand signal, not a sale — most challenges are scanners. Internal AgentCash self-pays are not external revenue; fleet external revenue is $0.00 unless the chain says otherwise.
- Paying for Lumi's high-value check adds a live re-check but never changes the verdict or score.
- No claim of a sale is made here; trust friction is one measurable part of machine-buyer acquisition, which remains the owner's stated priority over cold outreach.
