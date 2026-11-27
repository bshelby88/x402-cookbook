# Buyer card — MCP Buyer-Bridge Auditor (tool 57)

**What this grades:** the MCP tool surface an autonomous agent actually meets at
`https://raen-mcp-gateway.fly.dev/mcp` — tools/list discovery, input schemas,
advertised price vs the LIVE 402 challenge, canonical `payTo`, and free-backdoor refusal.

## Live run 2026-11-27 16:1xZ
- `tools/list`: HTTP 200, **5 tools** advertised, all with input schemas + required fields.
- `tools/call` with NO payment: **402 on all 5** — no free execution backdoor.
- Live 402: `scheme=exact`, `network=eip155:8453`, full canonical `payTo` on all 5.
- **2/5 advertised prices disagree with the live 402** (`DRIFT_WARN`):

| Tool | Description says | Live 402 charges | Flag |
|---|---|---|---|
| `raen_law_lookup` | $0.005 | $0.005 | OK |
| `raen_ticker_analysis` | $0.005 | $0.001 | PRICE_DRIFT |
| `raen_dispute_letter` | $0.10 | $0.01 | PRICE_DRIFT |
| `raen_image_generate` | $0.01 | $0.01 | OK |
| `raen_contract_analysis` | $0.005 | $0.005 | OK |

## Verdict
`DRIFT_WARN` — the bridge is buyable and canonical, but two tool descriptions are
truth-inconsistent with the charge. Pricing is **owner-gated**: this tool reports the
drift and never changes a price. An agent budgeting from `tools/list` descriptions
over-budgets on those two tools; the live 402 is authoritative.

`--check` exits 1 only on hard drift (payTo / scheme / network / free backdoor),
never on a missing payer or on owner-gated price drift.

Read-only, stdlib-only, no signing, no X-PAYMENT, no funds, no deploy.
