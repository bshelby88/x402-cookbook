# Recipe 56 — Lapsed Machine-Buyer Churn & Reactivation Auditor

**Problem:** The owner KPI is *repeat buyers x calls/payer*. Tools 50/55 measure the
repeat count; nothing measures lapse/churn or the reactivation lever, and the
collector's `revenue_external_usd` silently counts breadth-crawler dust as external.

**Tool:** `scripts/buyer-churn.py` — read-only, stdlib-only.

1. Fetch collector `/ledger.json` + `/stats`.
2. Load behaviour-discovered breadth crawlers from tool 51's live registry
   (`registry/breadth-detector.json`), with an embedded fallback.
3. Classify every ledger tx: internal (canonical / retired / AgentCash),
   breadth-crawler, or genuine_external. Crawlers/internals are excluded before KPI.
4. Aggregate genuine external payers: calls, spend, first/last call, distinct walls.
5. Flag `LAPSED` at >= 7 days and size a LIVE-priced return credit
   (`min(3 x live price, $0.05)`) redeemable via the claims desk (recipe 22).
6. Decode a LIVE 402 (x402 v2 `amount`) for pricing and a canonical-payTo drift guard.

**Live 2026-11-27:** 61 tx = 58 internal / 3 crawler / 0 genuine external.
`NO_GENUINE_BUYERS`, lapsed 0, honest external earned $0.00, collector's $0.012/24h
= crawler dust. Live wall $0.005 canonical. Auto-populates when a real buyer appears.

**Guards:** `--check` exits 1 only on canonical payTo drift or an internal/crawler
address misclassified as a buyer. No signing, no X-PAYMENT, no funds, no sends, no deploy.
