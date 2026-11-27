# 57. MCP Buyer-Bridge Auditor — can an MCP client actually buy from us?

The first 56 tools grade HTTP walls, docs, payers, ledgers, chains, funnels, paths,
repeat passports and churn. None grades the **MCP tool surface**, which is the one
surface that literally implements the owner's law "get autonomous agents to our
platforms": an agent client does not curl a wall, it calls `tools/list` and
`tools/call`. This tool grades that journey end-to-end, read-only.

## Runs
```bash
python3 scripts/mcp-bridge-auditor.py
python3 scripts/mcp-bridge-auditor.py --check        # CI gate: hard drift only
python3 scripts/mcp-bridge-auditor.py --out snap.json
```

## What it checks
1. **Discovery** — `tools/list` reachable, parses JSON or SSE frames, tool count > 0.
2. **Understand** — every tool has an `inputSchema` with named required fields.
3. **Gate** — `tools/call` with NO payment must return a 402 challenge; HTTP 200 is
   a `FREE_BACKDOOR` finding (output is never collected or repeated).
4. **Truth** — decode `payment-required`; require `scheme=exact`, `network=eip155:8453`,
   full canonical `payTo` (`0x9b8a27e03ceba490953cda8ab1291c0e13baf72f`).
5. **Price parity** — advertised `$X USDC` in the tool description vs the live
   `accepts[0].amount`. Mismatch is `PRICE_DRIFT` (WARN, owner-gated — never auto-fixed).

## Honest output — 2026-11-27 16:1xZ
5 tools, 5/5 canonical 402 gates, no free backdoor, **2 price drifts**:
`raen_ticker_analysis` ($0.005 described / $0.001 live) and `raen_dispute_letter`
($0.10 described / $0.01 live). Status `DRIFT_WARN`; `--check` exit 0.

## Refusal guards
No signing key, no X-PAYMENT header, no on-chain writes, no deploy, no external
sends. Only real advertised tool names are probed, always with empty arguments and
no payment, so no paid tool can execute. Snapshot `registry/mcp-bridge-auditor.json`;
buyer card `registry/mcp-bridge-auditor.md`.
