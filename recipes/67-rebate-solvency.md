# 67 — Rebate Promise Solvency Auditor

**Question it answers:** *The manifest promises "FREE FIRST CALL — net cost $0 via charge-and-rebate." Is that promise actually solvent, or will I pay full price and never see the rebate?*

Tool 64 grades whether the rebate hook is **disclosed** in the live 402. It does not check whether the rebater rail can **pay**. A "net cost $0" promise backed by a dry wallet, a disabled flag, or a drifted treasury is a conversion killer and a TRUTH violation. This tool closes that gap.

## Run it

```bash
python3 scripts/rebate-solvency.py
python3 scripts/rebate-solvency.py --check          # exit 1 only on a hard solvency break
python3 scripts/rebate-solvency.py --out registry/rebate-solvency.json
```

Stdlib only. No dependencies, no wallet, no signing, no `X-PAYMENT`, no funds moved, no price changed, no deploy.

## What it reads (all public)

| Source | Facts used |
|---|---|
| `royal-ruby-x402.fly.dev/.well-known/x402.json` + `/openapi.json` | advertised rebate promise, explicit `$X USDC` figure |
| `POST /api/law-lookup` (unpaid, no `X-PAYMENT`) | live x402 v2 `accepts[0]`: amount, payTo, scheme, network — the "full charged amount" the rail promises to return |
| `royal-ruby-rebater.fly.dev/health` | non-secret facts only: `treasury`, `rebatesEnabled`, `dailyCap`, `rebateCountToday` |
| Base RPC × 3 (`base.publicnode.com`, `mainnet.base.org`, `base.drpc.org`) | `eth_chainId` must be `0x2105`; `eth_call balanceOf` on native USDC `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`; `eth_getBalance` for gas |

## Verdicts

| Verdict | Meaning | `--check` |
|---|---|---|
| `SOLVENT` | Rail enabled, treasury is a known internal address, USDC + gas cover the rebate | 0 |
| `CAP_EXCEEDS_FLOAT` | Funded, but `dailyCap × rebate` exceeds the float | 0 (WARN) |
| `LOW_GAS` | USDC fine, Base gas below 0.00005 ETH | 0 (WARN) |
| `PROMISE_PRICE_MISMATCH` | Advertised rebate ≠ live 402 price | 0 (WARN, owner-gated) |
| `NO_PROMISE` | No rebate advertised — nothing to verify | 0 |
| `DISABLED` | Promise advertised but `rebatesEnabled != true` | **1** |
| `TREASURY_DRIFT` | Treasury is malformed or not a full-form known internal address | **1** |
| `UNFUNDED` | Treasury USDC < one rebate | **1** |
| `NO_CONSENSUS` / `MALFORMED` | Fewer than 2 clean chainId-validated RPCs, or RPC disagreement | **1** |

Address safety: the treasury is compared as a **full 42-char address** against canonical / retired / AgentCash. Poison homoglyphs (e.g. `0xfbc04a6b…42240` vs the real AgentCash `0xfbc0eb7811d477e55261d956df39f0046e192240`) classify as `UNKNOWN_ADDRESS` → `TREASURY_DRIFT`, never as funded.

## Live result — 2026-11-28 03:5xZ

```
verdict          SOLVENT
promise found    true     (manifest + OpenAPI)
advertised       $0.005   ("rebated $0.005 USDC")
live 402         $0.005   (v2 / exact / eip155:8453 / canonical payTo)
rebatesEnabled   true
treasury         0xfBC0eb7811D477E55261d956dF39f0046E192240  -> INTERNAL_AGENTCASH
float            11.515259 USDC + 0.00170255 Base ETH   (3/3 RPC consensus, chainId 0x2105)
coverage         2,303 rebates at $0.005; daily cap 100 = $0.50/day
--check          exit 0
self-test        7/7 verdict paths exact (SOLVENT/DISABLED/TREASURY_DRIFT/UNFUNDED/
                 NO_CONSENSUS/LOW_GAS/NO_PROMISE)
```

The first-call-free hook is **real and fundable**. No owner action needed. Snapshot: `registry/rebate-solvency.json`; buyer card: `registry/rebate-solvency.md`.

## Boundaries

Read-only. Never signs, pays, moves funds, changes a price, edits the queue, or deploys. The rebater's private key is never read or displayed — only its health endpoint's non-secret facts and its on-chain balance. Pricing and credential changes are owner-gated; this tool reports drift, it does not fix it.
