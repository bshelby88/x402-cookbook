# 60 — Wallet-Only Purchase Conformance Auditor

## The gap
The owner's law: **get autonomous agents to our platforms to create revenue.** An autonomous agent has a wallet — not an email, an account, a browser session, a phone number or a human turn. If a paid surface introduces an identity wall *before or at* the payment gate (required email / signup / account / API key / OAuth / KYC), the agent cannot complete a purchase: a lost sale with no money moved, invisible in the ledger.

Tools 1–59 grade the 402 wall (23/42/43), the docs (48/59), the payer (49/50/51), the ledger and chain (52), settlement (54), and the MCP bridge (57). None grades **wallet-only executability** — whether a funded wallet is sufficient to buy. This tool closes that face.

## What it does
Read-only, stdlib-only. No signing, no `X-PAYMENT`, no funds, no sends, no deploys. For each kept-live paid wall + the MCP gateway:

1. Sends one **unpaid** probe (the documented paid method/body).
2. Decodes the public 402 `payment-required` header and checks `accepts[0]` for `scheme=exact`, `network=eip155:8453`, canonical `payTo` (full 42-char, case-insensitive).
3. Reads the public manifest endpoint's schema + description and checks for **required identity fields** (`email`, `api_key`, `authorization`, `oauth`, `account`, `kyc`, `ssn`, …) and hard account/signup preconditions.
4. Confirms a **free discovery surface** returns 200 (an agent can inspect before paying).
5. Grades `WALLET_ONLY` / `IDENTITY_WALL` / `GAP` / `UNREACHABLE`.

`--check` exits 1 **only** on a HARD identity wall on a paid route. A documented optional credential alternative (e.g. "or a Bearer dev key"), a down page, an absent schema, or a price drift is a WARN/GAP → handoff, never an auto-fix. Pricing and credentials are owner-gated; the tool never changes either.

## Usage
```bash
python3 scripts/wallet-only-auditor.py                 # JSON posture report
python3 scripts/wallet-only-auditor.py --check          # CI: fail only on HARD identity wall
python3 scripts/wallet-only-auditor.py --self-test      # 5-case grader unit test
```

## Live result (2026-11-27 19:44Z)
4/4 kept-live paid surfaces `WALLET_ONLY`, zero identity walls, zero hard drifts. royal-ruby, contract-eye, nanobanana: canonical wallet gate + free discovery 200 + no identity fields. raen-mcp-gateway: canonical wallet gate + free `tools/list` 200 + one **WARN** — the manifest documents an *optional* Bearer dev key alternative to x402 (`tools/call requires an x402 payment or a Bearer dev key`); wallet-only purchase still works, so this is not a hard wall. `--check` exit 0.

## Honesty
A wallet-only gate is necessary but not sufficient for demand. As of this run external earned is **$0.00** and there are zero genuine machine buyers — the constraint is demand, not wall integrity. This tool guarantees that when a buyer arrives, no identity wall blocks the checkout; it does not itself create buyers.
