# Recipe 32 — Buyer failure triage + live doc-truth audit

**Innovation 2026-11-25 / verified 2026-11-26 (Tiffany, machine-buyer acquisition).** A machine
buyer's most expensive failure is not a broken service — it is a *silent re-challenge*: the
buyer follows the seller's own doc, attaches the wrong retry header, sees another 402, and
signs again. Recipe 23 verifies a wall you already know; recipe 25 checks this repository's
recipe text; recipe 31 audits the catalog. **This recipe audits the buyer-facing docs that
are actually live, and turns any observed HTTP outcome into a `do_not_repay` verdict.**
Read-only, stdlib-only, no signing, no `X-PAYMENT`, no money movement.

Script: [`scripts/failure-triage.py`](../scripts/failure-triage.py).
Run snapshot: [`registry/failure-triage-20261125.json`](../registry/failure-triage-20261125.json).

## Mode 1 — triage an observed failure

```bash
# Buyer followed the doc's PAYMENT-SIGNATURE advice and got another 402:
python3 scripts/failure-triage.py --status 402 --header-used PAYMENT-SIGNATURE \
  --url https://royal-ruby-x402.fly.dev/api/ping

# Paid, then the handler 500'd — is it safe to pay again?
python3 scripts/failure-triage.py --status 500 --paid \
  --body '{"error":"handler failed"}'
```

Every verdict carries `code`, `severity`, `do_not_repay`, `root_cause`, `fix`, and a
`reference` to the existing recipe that completes the action. When `--url` is given, the
tool re-probes the wall **unpaid** and attaches the current decoded challenge
(`scheme`, `network`, `amount`, full `payTo`, canonical verdict) as evidence.

| Observed | Code | `do_not_repay` | Next action |
|---|---|---|---|
| 402, no payment header | `EXPECTED_UNPAID_CHALLENGE` | no | Decode `accepts[0]`, verify full payTo, sign once, retry with `X-PAYMENT` (recipe 23) |
| 402 after `PAYMENT-SIGNATURE` | `STALE_RETRY_HEADER` | **yes** | Silent re-challenge — use `X-PAYMENT`; do not sign again (recipe 25) |
| 402 after `X-PAYMENT` | `PAYMENT_REJECTED` | **yes** | Compare signed terms to live challenge; look up tx if a settle occurred (recipe 27) |
| 401 / 403 | `AUTH_GATE` / `IDENTITY_WALL` | yes | Keys or owner-lane — payment cannot open these |
| 404 / 429 | `BAD_ROUTE` / `RATE_LIMITED` | yes | Re-read manifest / back off; never pay on these |
| 503, unpaid | `CAPABILITY_GATE` | yes | F1 settle-order gate: dead/quota key returns 503 with **no** 402; retry later |
| 5xx, payment attached | `SETTLED_NO_DELIVERY` | **yes** | Verify tx on-chain, use claims desk with tx hash (recipes 22 + 27) |
| 200 with `degraded:true` | `DEGRADED_DELIVERY` | — | TRUTH law: paid output was less than advertised; flag + claims desk |

Exit `0` = safe/clean, `1` = high-severity (do not repay), `2` = manual review.

## Mode 2 — audit the live buyer docs

```bash
python3 scripts/failure-triage.py --audit-docs \
  --out registry/failure-triage-20261125.json
```

Fetches seven router pages a machine is told to read (`/pricing.md`, `/faq.md`, `/faq.json`,
`/how-it-works.json`, `/pay-failed?format=json`, `/terms.md`, `/privacy.md`) and flags:

- `STALE_RETRY_HEADER` — doc teaches `PAYMENT-SIGNATURE` instead of the verified `X-PAYMENT`.
- `STALE_DOWN_CLAIM` — doc names a wall as down while its live manifest carries canonical `payTo`.
- `STALE_VERIFICATION` — cited date stamps older than 7 days.
- `RETIRED_PAYTO_TAUGHT` / `WRONG_NETWORK` — retired payee or Sepolia presented as a value.
  Occurrences framed as warnings ("reject", "wrong network", "never") are **not** flagged —
  `/pay-failed` correctly names both as things to avoid, and that is not a defect.

Exit `1` means at least one high-severity doc defect. The check is deliberately conservative:
it reports what the live bytes say, not what the docs intend.

## Shipped-state evidence (2026-11-26T00:26Z run)

Seven docs checked, all HTTP 200. **Nine findings**, reproduced in the snapshot:

1. `https://rae-fleet-router.fly.dev/pricing.md` — **high**: "re-send with the `PAYMENT-SIGNATURE`
   header". A buyer following the router's own pricing page gets a silent re-challenge.
2. `https://rae-fleet-router.fly.dev/how-it-works.json` — **high**: step 4 ("Sign + pay")
   carries the same stale header. Both are the exact defect recipe 25 guards *inside this
   repo* but which survives on the live surface.
3. `/faq.md` and `/faq.json` — **medium** `STALE_DOWN_CLAIM`: list `contract-eye` as down per
   a 2026-09-28 recovery matrix, while today's live probe shows
   `contract-eye-x402.fly.dev/.well-known/x402.json` carrying canonical `payTo`
   `0x9b8a27e03CEbA490953cDa8AB1291c0E13bAf72f` (8 occurrences, zero retired) and a live
   402 of `5000` atomic ($0.005) with canonical payTo.
4. Five `STALE_VERIFICATION` findings — `/faq.md`, `/faq.json`, `/how-it-works.json`,
   `/terms.md`, `/privacy.md` still cite `2026-10-02` / `2026-09-28` as "verified".

Corroborating live read in the same pass: royal-ruby `/api/ping` 402 → `exact` /
`eip155:8453` / `1000` atomic / canonical payTo; contract-eye 402 → `5000` atomic canonical;
gateway `tools/call` 402 → `50000` atomic canonical (`tools/list` is the free 200 gate).
`royal-ruby-x402.fly.dev/pricing.md` 404 — the FAQ's claim of "12 walls serving /pricing.md
200" is stale; price truth stays the live 402.

**These are seller-side doc defects, not wall outages.** Repair needs a router source change
plus a deploy; the router is inside the owner's BURN FREEZE, so this recipe ships the evidence
and a corrected copy pack (`rae-fleet-router/fleet_db/PLAN-67-faq-copy.md`), not a deploy.
No agent redeployed, restarted, or scaled anything.

## What it deliberately does NOT do

It does not sign an EIP-3009 authorization, attach a real payment header, or settle.
`--url` probes are unpaid GET/POST only. It does not publish or send anything externally.
It does not change the router; it reports live truth and hands the fix to the owner.

## Where to go next

- [Recipe 23 — buyer preflight](23-buyer-preflight.md) (verify a known wall before signing)
- [Recipe 25 — payment-header conformance](25-payment-header-conformance.md) (repo-side header guard)
- [Recipe 27 — buyer receipt](27-buyer-receipt.md) (prove a settle on-chain)
- [Recipe 31 — catalog parity](31-catalog-parity.md) (find live walls the catalog forgot)
