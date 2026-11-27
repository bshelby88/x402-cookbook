# Machine-Buyer Acquisition Funnel — live snapshot (2026-11-27 05:30Z)

For autonomous agents evaluating RAEN's paid APIs: the full funnel from discovery
to repeat purchase, scored from live read-only probes. The live 402 challenge is
authoritative over this snapshot.

| Service | DISCOVER | UNDERSTAND | PAY | REPEAT | Verdict |
|---|---|---|---|---|---|
| royal-ruby | yes | canonical | exact / eip155:8453 / $0.005 | no genuine external payer | BLOCKED_AT_REPEAT |
| contract-eye | **absent from router catalog** | canonical | exact / eip155:8453 / $0.005 | no genuine external payer | BLOCKED_AT_DISCOVER |
| nanobanana | yes | canonical | exact / eip155:8453 / $0.01 | no genuine external payer | BLOCKED_AT_REPEAT |
| raen-mcp-gateway | **absent from router catalog** | canonical | exact / eip155:8453 / $0.05 | no genuine external payer | BLOCKED_AT_DISCOVER |

- **Canonical payTo:** `0x9b8a27e03ceba490953cda8ab1291c0e13baf72f` (all four live 402s)
- **Catalog:** `https://rae-fleet-router.fly.dev/catalog.json` (HTTP 200 this run)
- **Honest external earned:** $0.00 — internal test traffic and breadth-crawler
  dust (`0xc9c7b38c…1670`, `0x171d8021…50fca`) are excluded, not counted as buyers.
- **Pay:** all four walls return canonical x402 v2 challenges; the gateway $0.05
  is a standing owner-gated price decision, not a payTo defect.
- **Repeat:** no service has a genuine returning external buyer yet. This is the
  owner's KPI (repeat buyers × calls/payer) measured honestly.

Tool: `scripts/acquisition-funnel.py` · Recipe: `recipes/53-acquisition-funnel.md`
Read-only, stdlib-only, no signing, no X-PAYMENT, no funds, no deploy.
