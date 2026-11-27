# Buyer card — Volume-Tier Truth Auditor (tool 58)

**What this grades:** the price an autonomous buyer actually gets when it scales up.
Tools 23/24/46 read the BASE 402 only; this one probes the SAME paid route at the
base call and at every documented bulk quantity, decodes `payment-required` on each,
and checks the ladder is canonical and monotonic.

## Live run 2026-11-27 17:2xZ

| Wall | Base 402 | Advertised tiers | Live tiers | Verdict |
|---|---|---|---|---|
| royal-ruby | $0.005 | manifest: 10–99 @ $0.002, 100–500 @ $0.001, floor 10 | bulk5/9 → $0.005 (floor held); bulk10/50 → $0.002/citation; bulk100/500 → $0.001/citation | **OK — tier ladder real and canonical** |
| contract-eye | $0.005 | cookbook: 10–99 @ $0.002, 100+ @ $0.001 | bulk10/100 → flat $0.005; manifest says nothing about bulk | **DOC_DRIFT — advertised discount not honored** |
| nanobanana | $0.01 | cookbook: 10+ @ $0.008 | bulk10 → flat $0.01; manifest says nothing about bulk | **DOC_DRIFT — advertised discount not honored** |

Every probe returned x402 v2 `scheme=exact`, `network=eip155:8453`, full canonical
`payTo` (`0x9b8a27e03ceba490953cda8ab1291c0e13baf72f`), canonical USDC asset,
integer `amount`. Zero hard drift.

**Additional finding:** royal-ruby's own manifest `x-guidance` still says
"$0.05 per call ($0.03 for some wallets in a price test)" — 10× the live $0.005
base, and it lists only the 100–500 tier (omits 10–99). The live 402 is authoritative.

## Verdict
`DOC_DRIFT_WARN` — one wall's volume ladder is real and truthful; two cookbook
price claims describe discounts the live 402s do not give. A machine buyer budgeting
a 100-call batch on contract-eye from the cookbook would budget $0.10 and be
charged $0.50 (5×). Pricing/docs are **owner-gated**: this tool reports and never
changes a price.

`--check` exits 1 only on HARD drift (non-canonical payTo / scheme / network / asset,
non-integer amount, non-monotonic tier, broken floor, or a tier above base) —
never on doc drift or a missing payer.

Read-only, stdlib-only, no signing, no X-PAYMENT, no funds, no deploy.
