# Machine-Buyer Readiness Scorecard

Generated 2026-11-26T13:31:27.985446+00:00 - buyer-readiness/1.0. Scores come ONLY from live unpaid reads; no funds moved.

| Wall | Score | Grade | Live price | Paid path | Warnings |
|---|---|---|---|---|---|
| royal-ruby | 90/100 | READY | $0.0500 | canonical | manifest price missing (live 402 authoritative) |
| contract-eye | 80/100 | READY | $0.0050 | canonical | llms.txt missing canonical payTo: canonical payTo absent |
| nanobanana | 80/100 | READY | $0.0100 | canonical | llms.txt missing canonical payTo: canonical payTo absent |
| raen-mcp-gateway | 70/100 | PARTIAL | $0.0500 | canonical | llms.txt missing canonical payTo: canonical payTo absent; no independent trust record: no trust record |

**Where to spend first:** highest READY score, verified `canonical` paid path, then retry with the seller's documented `X-PAYMENT` header. Never pay a wall whose paid path reads `BREAK` or whose `payTo` is not the full canonical `0x9b8a27e03ceba490953cda8ab1291c0e13baf72f`.

A WARN (missing manifest price, absent llms.txt payTo, no trust record) is buyer friction, not a payment break - the live 402 is always authoritative.
