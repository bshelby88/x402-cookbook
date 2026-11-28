# 66. Facilitator Capability-Discovery Auditor

**Question it answers:** a spec-compliant autonomous buyer client calls `GET /supported`
on the facilitator before it builds an EIP-3009 authorization (x402 spec v1 + v2, §7.3).
Can it discover RAEN's capabilities at that path — and does the facilitator actually
cover the kind each kept-live wall advertises?

**Why this is a new acquisition axis:** tools 42/48/57/62/65 grade the *challenge* and
its fields/determinism; tools 29/34/41/47/59 grade *discovery* surfaces; but none of
tools 1-65 grade the *facilitator's own machine-readable capability contract* — the
thing a standards-based client reads before it can even construct a payment.

## Run

```bash
python3 scripts/facilitator-support.py            # human report
python3 scripts/facilitator-support.py --json     # machine report
python3 scripts/facilitator-support.py --check    # exit 1 only on BLOCKED
```

Stdlib-only, read-only. Never signs, never pays, never sends `X-PAYMENT`, never
changes a price, never moves funds.

## What it grades

1. **Spec discovery path** — `GET <facilitator>/supported`; validates the §7.3
   contract (`kinds[]` with `x402Version`/`scheme`/`network`, plus `extensions`
   and `signers`).
2. **RAEN path** — `GET <facilitator>/facilitator/supported` (the FastAPI-prefixed
   location discovered from the facilitator's `/openapi.json`).
3. **Kind parity** — decode each kept-live wall's unpaid 402 and check that its
   `(x402Version, scheme, network)` tuple is present in the active `kinds[]`.
4. **Payee parity** — check each wall's `payTo` against the facilitator's
   `servedPayees`.
5. **Verdict** — `READY` / `COMPAT_GAP` (capability discoverable, but not at the
   spec path) / `BLOCKED` (no valid discovery contract, or a wall kind is uncovered).

`--check` fails only on `BLOCKED`. `COMPAT_GAP` is a report-only compatibility
handoff: the payment path works, spec-path discovery does not. Pricing is
owner-gated and is never treated as a defect by this tool.

## 2026-11-28 01:5xZ live result

- `GET /supported` → **HTTP 404** (spec path absent).
- `GET /facilitator/supported` → **HTTP 200**, valid contract, kinds =
  `(2, exact, eip155:8453)` and `(1, exact, base)`, `signers.eip155:*` =
  `0x6289b753…604a3b`.
- 4/4 walls (royal-ruby, contract-eye, nanobanana, gateway) → kind `COVERED`,
  payee `COVERED`, all `v2/exact/eip155:8453`, full canonical payTo.
- Verdict **`COMPAT_GAP`**, `--check` exit 0. No payment-path break, no hard drift.
- Handoff to `[kip][staci]`: add a root-level `GET /supported` alias to the
  facilitator (or document the `/facilitator/supported` prefix in buyer docs) so
  spec-compliant clients can discover capabilities. No pricing action, no deploy
  by this tool. See `registry/facilitator-support.json` and the buyer card.
