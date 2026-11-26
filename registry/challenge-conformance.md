# Can your x402 client actually pay these walls? (live conformance, 2026-11-26)

Read the machine-readable snapshot at `registry/challenge-conformance.json`.
Generated from unpaid POST/GET/HEAD probes at 2026-11-26T12:20Z. No account, no
key, no signing, no payment was used.

**Answer: yes on the paid POST path, all four walls canonical, zero price drift.
One read-probe caveat below.**

| Wall | Pay method | Live price | Challenge |
|---|---|---|---|
| royal-ruby — consumer-law citations | POST `/api/law-lookup` | $0.05 | canonical, decodable |
| contract-eye — contract clause risk | POST `/api/analyze-contract` | $0.005 | canonical, decodable (GET/HEAD too) |
| nanobanana — AI image generation | POST `/api/generate-image` | $0.01 | canonical, decodable (GET/HEAD too) |
| raen-mcp-gateway — law lookup via MCP | `tools/call` | $0.05 | canonical, decodable (GET/HEAD too) |

Every canonical challenge: `x402Version: 2`, `scheme: exact`,
`network: eip155:8453`, full canonical payTo
`0x9b8a27e03ceba490953cda8ab1291c0e13baf72f`, integer `amount` in USDC atomic
units. Gateway `tools/list` is free discovery and correctly returns 200.

**Caveat — royal-ruby GET/HEAD:** these return 402 but with no `payment-required`
header, so a client that reads the resource before paying gets an undecodable
challenge. Use POST (the advertised, canonical method). Generic graders may mark
that read probe `no_go`; a fix is handed to BEAN/CROWN. This is published as a
gap, not hidden.

**Caveat — royal-ruby manifest:** its `accepts` block has no `price` field. The
live 402 ($0.05) is authoritative; read the challenge, not the manifest.

Verify any of it yourself, free:

```bash
python3 scripts/challenge-conformance.py
# prints full JSON; exit 0 = all advertised paid methods canonical
```

Truth: coordination = Library, money = chain, code = GitHub, runtime = live probes.
External earned revenue remains **$0.00** — this is a truth/acquisition asset, not a sale.
