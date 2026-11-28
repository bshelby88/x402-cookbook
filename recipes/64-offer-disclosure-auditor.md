# 64. Acquisition-Offer Disclosure Auditor

**The gap.** Tools 1-63 grade the wall, the docs, the payer, the ledger, the chain, and even individual offers (volume tiers #58). None grades the one surface an autonomous buyer actually reads *at the moment of sale*: the live, unpaid 402 response body. RAEN's own buyer tooling (#44 client-bootstrap, #45 agent-skillcard) teaches agents to derive every value from that 402. When a service advertises an acquisition offer in its public manifest but omits it from the live 402, a 402-first buyer never discovers the hook and pays full price.

**The tool.** `scripts/offer-disclosure.py` (stdlib, read-only) does one unpaid `GET /.well-known/x402.json` and one unpaid paid-route `POST` per kept-live wall, then grades four acquisition offers as `GAP` (manifest promises, 402 omits), `OK`, or `N/A`:

| offer | signals |
|---|---|
| `first_call_free` | first call free / charge-and-rebate / `x-payer-address` / rebate |
| `bulk_volume` | bulk / volume tier / per-citation / 100-500 |
| `redeem_recovery` | redeem / already settled / claim-at-desk |
| `free_dev_key` | `/keys/request` / free developer key |

Disclosure is read from the 402 body **and** its nested machine-readable surfaces (`payment_instructions`, `paymentInstructions`, `extensions`, `resource`, `offers`) — not from the marketing manifest. A 2xx on a paid call is a `FREE_BACKDOOR` hard defect; a retired payTo or non-canonical envelope is hard drift. `--check` fails on any gap or drift. Nothing is signed, no X-PAYMENT is sent, no funds move, no key is used, no deploy happens.

## Live run — 2026-11-28 00:20Z

Verdict `DISCLOSURE_GAPS`: 4/4 walls reachable and canonical (`exact` / `eip155:8453` / full canonical payTo / positive integer amount), 0 hard drift, **1 disclosure gap**.

| wall | first_call_free | bulk_volume | redeem_recovery | free_dev_key |
|---|---|---|---|---|
| royal-ruby | **GAP** | OK | OK | N/A |
| contract-eye | N/A | N/A | N/A | N/A |
| nanobanana | N/A | N/A | N/A | N/A |
| raen-mcp-gateway | OK | N/A | N/A | OK |

**Finding.** `royal-ruby` advertises `firstCallFree: true` plus a charge-and-rebate `offers[]` entry and `x-payer-address` guidance in its manifest. Its live 402 body discloses the bulk ladder (schema) and the redemption path (`payment_instructions.already_settled_redeem`), but never mentions the rebate hook. A buyer following RAEN's own 402-first tooling pays $0.005 in full and never learns the first call could be free. The gateway, by contrast, discloses both its first-call-free and free-dev-key hooks inside `payment_instructions` — the correct pattern.

This is a **disclosure** gap, not a paywall break or a price defect. Handoff (owner-gated, burn freeze respected): add one sentence to royal-ruby's 402 `payment_instructions` naming `x-payer-address` and the charge-and-rebate net-$0 first call. This tool reports it; it does not deploy or change any price.

## Usage

```bash
python3 scripts/offer-disclosure.py --check
python3 scripts/offer-disclosure.py --out registry/offer-disclosure.json
```

Exit `0` = all offers disclosed and canonical, `1` = gap/drift, `2` = no wall reachable. Snapshot: `registry/offer-disclosure.json`. Buyer card: `registry/offer-disclosure.md`.

Read-only, stdlib-only. No signing, no X-PAYMENT, no funds, no keys, no posting, no deploy. Burn freeze respected (kept-live walls only).
