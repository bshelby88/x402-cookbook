# 46. Budget Guard — a live-priced spend cap for autonomous buyers

The other 45 cookbook tools answer *which wall, is the challenge honest, how do I
pay, did I get a receipt*. None answers the question an autonomous agent must
answer **before it signs anything**: *can I afford this basket of calls within my
budget?* Agents operate under spend limits; without a deterministic go/no-go
priced from live facts, the rational behavior is to abstain — which is exactly
the acquisition failure this tool removes.

`scripts/budget-guard.py` is a read-only, stdlib-only spend planner. It sends
**one unpaid POST** per kept-live paid wall, base64-decodes the x402 v2
`payment-required` header, and reads the price / payTo / network / scheme from
the **live challenge itself** — never from a hand-maintained table. It then
takes a planned basket and a USDC budget and emits an AFFORDABLE / OVER_BUDGET
verdict, the per-wall cost, the affordability frontier (max calls that fit), and
a copy-ready agent budget policy.

## Why this is a machine-buyer acquisition asset

- **Removes the abstain-by-default blocker.** An agent with a budget cap can now
  *prove* a purchase fits before it commits, using live prices.
- **Spend policy as data.** The emitted `agent_policy` is a JSON object an agent
  can embed directly in its own config (payTo allowlist, per-call caps, reserve,
  drift-abstain rule).
- **Guardrails are structural.** Full 42-char canonical payTo compare (poison /
  retired address safe), `exact` scheme, `eip155:8453`, integer `amount > 0`.
  Any drift flips the verdict to `DRIFT` and the policy rule to `ABSTAIN`.
- **Retry-safe by design.** A configurable reserve (default 10%) keeps budget
  for retries and the claims desk — the silent-rechallenge / double-pay trap
  that recipe 32 flags.

## Run

```bash
python scripts/budget-guard.py --budget 0.10 --reserve-pct 10 \
  --call royal-ruby=5 --call contract-eye=2 \
  --out-json registry/budget-guard.json --out-md registry/budget-guard.md
```

- `--budget` total USDC budget (default `0.05`)
- `--reserve-pct` percent held back for retries/claims (default `10`)
- `--call WALL=N` planned calls, repeatable; with no `--call`, the default basket
  is one call per wall
- Exit `0` = all walls canonical (AFFORDABLE **and** OVER_BUDGET both exit 0 —
  affordability is a buyer decision, not a trust failure); `1` = canonical drift;
  `2` = no wall reachable

## What it emits

`registry/budget-guard.json` — full live snapshot: per-wall `http_status`,
`price_usdc`, `price_atomic`, `payto`, `canonical`, `scheme`, `network`,
`planned_calls`, `planned_cost_usdc`, `max_calls_in_budget`, plus the aggregate
`verdict`, `total_planned_cost_usdc`, and `agent_policy`.

`registry/budget-guard.md` — a buyer-facing spend card plus a copy-ready JSON
budget policy.

## Live result (2026-11-26)

Verdict `AFFORDABLE`: 4/4 kept-live walls canonical, 0 drift, live prices
royal-ruby `$0.005` / contract-eye `$0.005` / nanobanana `$0.01` /
raen-mcp-gateway `$0.05`, all `exact` / `eip155:8453` / full canonical payTo,
integer `amount`. Default basket `$0.07` against `$0.09` usable (a `$0.10`
budget with 10% reserve). Affordability frontier: royal-ruby 8, contract-eye 8,
nanobanana 4, gateway 0 at the `$0.045`-usable stress case.

Only unpaid POSTs were sent. **No signing, no `X-PAYMENT`, no RPC money call,
no funds moved, no key used, no deploy** (BURN FREEZE respected — kept-live walls
only). The live 402 is always authoritative over the snapshot's timestamp.
