# Innovation 62 — x402 Challenge Constructability Auditor

Read-only, stdlib-only. An autonomous buyer cannot pay from a price alone: it
must construct a valid EIP-3009 payment authorization. This tool decodes each
LIVE 402 challenge (unpaid POST, no X-PAYMENT) and verifies the buyer has every
field needed to build that payment, and that header- and body-reading clients
agree.

## What it grades (the gap tools 48/57/58/61 leave open)
- Gate envelope: `exact` / `eip155:8453` / full canonical payTo / canonical Base USDC.
- EIP-3009 constructability: `amount` (>0), `maxTimeoutSeconds`, `extra.name`
  and `extra.version` (the EIP-3009 domain a typed-data signature needs),
  top-level `resource` descriptor, `x402Version`.
- Header vs body agreement on payTo and integer amount (body-reading clients).
- Body machine-readability; a 200 on a paid call is a FREE_BACKDOOR hard defect.
- WARN only (owner-gated): prices outside the acquired-data winner band
  ($0.003-$0.01, from the consolidated 88,788-resource world audit).

`--check` exits nonzero ONLY on hard gate/constructability defects. Pricing is
owner-gated: this tool never changes a price, never signs, never pays, never
moves funds, never deploys.

## Run
```
python3 scripts/challenge-fields.py            # live grade of 8 kept-live paid walls
python3 scripts/challenge-fields.py --check     # CI: nonzero on hard defects
python3 scripts/challenge-fields.py --self-test # 7 mocked constructability cases
```

## 2026-11-27 live result
8/8 paid walls CONSTRUCTIBLE, 0 hard defects, --check exit 0. All 8 carry the
full EIP-3009 constructability set. `gateway:ticker` at $0.001 sits below the
acquired-data winner floor $0.003 (WARN, owner-gated) — consistent with the
advertised-$0.005/live-$0.001 drift already handed off from tools 57 and 61.
Snapshot: `registry/challenge-fields.json`.
