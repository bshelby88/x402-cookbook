# x402 Challenge Determinism (buyer card)

Generated live 2026-11-28 01:40Z from 3x identical unpaid 402 probes. The live 402 remains authoritative over this snapshot.

**Why it matters to a machine buyer:** your preflight and budget are computed from a 402. If the next identical request returns a different price, payTo or network, you can silently overpay, underpay or pay the wrong address. This card records whether the challenge is stable across repeated identical requests.

- **Verdict:** `DETERMINISTIC` — 8/8 target surfaces STABLE across 3 probes, 100%.
- **No drift** in price, payTo, network, scheme, asset, timeout, EIP-3009 domain (`extra.name`/`version`) or `resource`.
- All 8 surfaces canonical: `exact` / `eip155:8453` / full canonical payTo `0x9b8a27e03ceba490953cda8ab1291c0e13baf72f` / Base USDC.
- Prices observed (stable across all 3 probes): law lookup $0.005, contract analysis $0.005, image gen $0.010, dispute letter $0.010, ticker $0.001, remaining gateway tools $0.005.

A machine buyer can safely cache the decoded envelope for a short window: identical probes returned identical canonical challenges. Re-run `scripts/determinism.py --check` before trusting a cached policy after any known fleet deploy. Full evidence in `registry/determinism.json`.
