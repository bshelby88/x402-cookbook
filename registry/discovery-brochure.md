# Discovery Brochure Auditor — buyer card (innovation 59)

Generated live by `scripts/discovery-brochure.py`. The public buyer-facing
"brochure" is the first surface a machine buyer (or its code generator) reads.
This card grades the storefront window for liveness and payTo safety.

**Live verdict 2026-11-27 18:32Z: CANONICAL — 8/8 surfaces live, 0 hard drift, 0 warns.**

| Surface | HTTP | Bytes | canonical payTo | verdict |
|---|---|---|---|---|
| Cookbook README (raw) | 200 | 37817 | present (retired addr appears ONLY as a "Reject the retired wallet" warning) | LIVE_CANONICAL |
| first-call-free Pages | 200 | 9282 | present | LIVE_CANONICAL |
| payback-calculator Pages | 200 | 7329 | not expected | LIVE_INFO |
| x402-scorecard Pages | 200 | 7281 | present | LIVE_CANONICAL |
| raen-law-pages | 200 | 8220 | not expected | LIVE_INFO |
| agent directory llms.txt | 200 | 49184 | present (x2) | LIVE_CANONICAL |
| router catalog.json | 200 | 35376 | present (x40) | LIVE_CANONICAL |
| MCP Registry listing (search=raen) | 200 | 4423 | not expected | LIVE_INFO |

Canonical payTo (full, case-insensitive): `0x9b8a27e03ceba490953cda8ab1291c0e13baf72f`.
Retired payTo `0x7861db4efc14a1ed5dd8c96c528a3796560f1393` is accepted ONLY in an
explicit rejection/retirement warning — never as a pay target (context-aware
grading, self-tested). Homoglyph near-matches (Hamming <=2) are flagged.

Read-only: no signing, no X-PAYMENT, no funds, no deploy, no sends. `--check`
exits 1 ONLY on an un-warned retired-payTo leak; a down page is a GAP handed
off, never silently auto-fixed. Fleet telemetry is public and unedited:
https://settlement-collector.fly.dev/stats
