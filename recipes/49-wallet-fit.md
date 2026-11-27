# 49. Buyer Wallet Fit Check — can THIS wallet actually pay, and will it count?

*Tiffany Innovation 49 · 2026-11-27 · read-only, stdlib-only, no signing, no funds moved, no deploy.*

## The gap this closes

The 48 prior cookbook tools all grade the **seller or the journey**:

- 23 `buyer-preflight`, 43 `buyer-readiness`, 42 `challenge-conformance` grade the **wall**.
- 33 `address-guard` classifies addresses **in text**.
- 24 `fleet-price-oracle`, 46 `budget-guard` price a basket from live 402s but never read the payer's **chain state**.
- 27 `buyer-receipt` proves settlement **after** the money has moved.

None answers the question an autonomous pay-er must answer *before* it signs:

> "Does my wallet actually hold enough USDC on the right chain — and will this payment be recognized as a real external purchase, or will it be written off as internal testing / crawler dust?"

That question is the mirror image of wall preflight, and it is the one that explains this fleet's actual evidence: **2,711 challenges, 11 verified settles, and $0.00 external revenue earned.** A funded-looking wallet that is a known breadth-crawler or an internal wallet generates challenges and dust, not demand. This tool makes that distinction deterministically, from the chain, before the buyer commits.

## What it does

`scripts/wallet-fit.py` (Python 3 stdlib only — `urllib`, `json`, `base64`, `re`, `argparse`):

1. **Live price** — one unpaid `GET` to a paid wall (default `royal-ruby-x402.fly.dev/api/law-lookup`). Decodes the x402 v2 `payment-required` header and takes `accepts[0].amount` — the price that will actually be charged. Full 42-char, case-insensitive `payTo` canonical guard. `--expect-usdc` is the honest fallback when no wall is reachable.
2. **USDC fit** — `balanceOf(buyer)` on Base USDC `0x833589fC…A02913` across 3 independent RPCs, with **consensus** (majority value, ≥2 agreeing). No single-RPC false zero.
3. **Gas** — `eth_getBalance` on Base (informational: EIP-3009 gas is often facilitator-sponsored).
4. **Chain coverage** — ETH-mainnet USDC balance (informational, per the chain-coverage law; the pay wall settles on Base only).
5. **Buyer role** — classifies the payer against the full canonical / retired / AgentCash addresses and the recorded breadth-crawler `0xc9c7b38c0942914fc8ea12063bc92dcd3b581670` (TIFF-BUYER-05: 156 payees / 6.4d, p50 $0.003 — dust-excluded, **not demand**).

Verdicts: `READY` · `INSUFFICIENT_USDC` · `INTERNAL_CANONICAL` · `INTERNAL_RETIRED` · `INTERNAL_AGENTCASH` · `KNOWN_CRAWLER` · `DRIFT` · `UNREACHABLE`.
Exit `0` = READY; `1` = cannot/should not pay; `2` = fetch/unreachable. CI-safe.

## Run it (costs nothing — it never signs or settles)

```bash
python3 scripts/wallet-fit.py 0xYOUR_BUYER_ADDRESS
python3 scripts/wallet-fit.py 0xYOUR_BUYER_ADDRESS \
  --wall https://royal-ruby-x402.fly.dev/api/law-lookup \
  --out-json registry/wallet-fit.json --out-md registry/wallet-fit.md
```

## Live results (2026-11-27, all four verdict paths exercised against real RPC reads)

Live wall: HTTP 402, `exact` / `eip155:8453` / amount `5000` = **$0.005**, canonical `payTo`.

| Buyer address (full) | Base USDC (3-RPC consensus) | Verdict | Exit |
|---|---|---|---|
| `0x9b8a27e03ceba490953cda8ab1291c0e13baf72f` (canonical) | 18.229907 | `INTERNAL_CANONICAL` | 1 |
| `0xfbc0eb7811d477e55261d956df39f0046e192240` (AgentCash) | 1.527259 | `INTERNAL_AGENTCASH` | 1 |
| `0xc9c7b38c0942914fc8ea12063bc92dcd3b581670` (known crawler) | **100.330205** | `KNOWN_CRAWLER` | 1 |
| `0x1111111111111111111111111111111111111111` (external) | 281.986988 | `READY` | 0 |

**The instructive case is the crawler:** it holds 100.33 USDC — far above the $0.005 price — so a balance-only check would call it READY. This tool blocks it (`KNOWN_CRAWLER`, exit 1) because its payments are recorded breadth-class dust, not demand. That is exactly the misbooking the collector's external bucket has suffered from, and it is the check no other cookbook tool performs.

Registry snapshot `registry/wallet-fit.json` + buyer card `registry/wallet-fit.md` are generated from the crawler case.

## Truth constraints

- **Money truth is the chain.** Balances are read from public RPCs with consensus; the price comes from the live 402, never a hand-maintained table. The live 402 is authoritative over any snapshot.
- **Chain scope** — fit is judged on Base (`eip155:8453`), the settlement chain; ETH-mainnet is reported as information only.
- **No trust in a seller dashboard.** The tool does not call the collector or any RAEN service for the buyer's standing; it uses the chain and the recorded crawler attribution.
- **Not a revenue claim.** External revenue earned remains **$0.00** on-chain truth. This is a buyer-safety/acquisition surface.
- No signing, no EIP-3009 authorization, no `X-PAYMENT`, no RPC money call, no funds moved, no deploy, no external send. BURN FREEZE respected (kept-live walls only).

## Where to go next

- [Recipe 23 — buyer preflight (verify the wall)](23-buyer-preflight.md)
- [Recipe 46 — budget guard (price the basket)](46-budget-guard.md)
- [Recipe 27 — buyer receipt (prove the settle)](27-buyer-receipt.md)
- [Recipe 32 — failure triage (retry safely)](32-failure-triage.md)
