#!/usr/bin/env python3
"""RAEN buyer receipt verifier - prove an x402 payment landed on Base (stdlib only).

READ-ONLY. This script never signs, never builds a payment header, never sends
funds, and never moves money. It calls eth_getTransactionReceipt /
eth_getTransactionByHash on a public Base RPC and decodes the ERC-20 USDC
Transfer logs to prove that a settlement actually reached the canonical
RAEN payTo address.

This closes the buyer's post-payment TRUTH gap (Tiffany Innovation 21). A
machine agent that can PROVE a payment landed on-chain -- without trusting the
seller's dashboard -- will actually complete the first paid call.

Usage:
  python3 scripts/receipt-verifier.py <txhash>
  python3 scripts/receipt-verifier.py <txhash> --expect-amount 0.05
  python3 scripts/receipt-verifier.py <txhash> --rpc https://base.publicnode.com

Exit codes:
  0 = VERIFIED: tx succeeded and USDC reached canonical payTo (>= expected)
  1 = NOT VERIFIED: tx exists but failed / no canonical transfer / short amount
  2 = TRANSPORT: bad args, tx not found, or RPC unreachable
"""
import argparse
import json
import re
import subprocess
import sys

CANONICAL_PAYTO = "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f"
USDC_BASE = "0x833589fcd6edb6e08f4c7c32d4f71b54bdA02913"
# keccak256("Transfer(address,address,uint256)")
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
DEFAULT_RPC = "https://base.publicnode.com"
TX_RE = re.compile(r"^0x[a-fA-F0-9]{64}$")


def rpc_call(rpc, method, params, timeout=25):
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    proc = subprocess.run(
        ["curl", "-s", "--max-time", str(timeout), rpc,
         "-H", "Content-Type: application/json", "--data-raw", json.dumps(payload)],
        capture_output=True, text=True, timeout=timeout + 15,
    )
    try:
        resp = json.loads(proc.stdout)
    except Exception:
        return None, "non-JSON RPC response: " + proc.stdout.strip()[:120]
    if "error" in resp:
        return None, "RPC error: " + str(resp["error"])[:160]
    return resp.get("result"), None


def verify(tx_hash, expect_amount=None, rpc=DEFAULT_RPC):
    receipt, err = rpc_call(rpc, "eth_getTransactionReceipt", [tx_hash])
    if err:
        return 2, {"verified": False, "status": "TRANSPORT_ERROR", "error": err}
    if not receipt:
        return 2, {"verified": False, "status": "TX_NOT_FOUND",
                   "note": "no receipt - wrong chain, pending, or bad hash"}

    tx, _ = rpc_call(rpc, "eth_getTransactionByHash", [tx_hash])
    status = receipt.get("status")
    succeeded = status in ("0x1", "0x01", 1)
    transfers = []
    canonical_total = 0.0
    logs = receipt.get("logs", []) or []
    for log in logs:
        topics = log.get("topics", []) or []
        if not topics or topics[0].lower() != TRANSFER_TOPIC:
            continue
        if (log.get("address") or "").lower() != USDC_BASE.lower():
            continue
        to = ("0x" + topics[2][-40:]) if len(topics) > 2 and len(topics[2]) >= 40 else ""
        frm = ("0x" + topics[1][-40:]) if len(topics) > 1 and len(topics[1]) >= 40 else ""
        raw = log.get("data", "0x")
        try:
            amount = int(raw, 16) / 1e6 if raw and raw != "0x" else 0.0
        except Exception:
            amount = 0.0
        is_canon = to.lower() == CANONICAL_PAYTO.lower()
        transfers.append({"from": frm, "to": to, "amount_usdc": amount,
                          "to_canonical": is_canon})
        if is_canon:
            canonical_total += amount

    result = {
        "verified": False,
        "status": "NOT_VERIFIED",
        "chain": "eip155:8453 (Base)",
        "tx": tx_hash,
        "block": receipt.get("blockNumber"),
        "tx_success": succeeded,
        "from": (tx or {}).get("from"),
        "canonical_payto": CANONICAL_PAYTO,
        "usdc_transfer_count": len(transfers),
        "usdc_to_canonical": round(canonical_total, 6),
        "transfers": transfers,
    }
    reason = []
    if not succeeded:
        reason.append("tx_failed")
    if canonical_total <= 0:
        reason.append("no_usdc_transfer_to_canonical_payto")
    if expect_amount is not None and canonical_total + 1e-9 < float(expect_amount):
        reason.append("short_amount")
    if reason:
        result["reason"] = reason
        return 1, result
    result["verified"] = True
    result["status"] = "VERIFIED"
    result["note"] = "USDC settlement to canonical payTo confirmed on Base"
    return 0, result


def main():
    ap = argparse.ArgumentParser(description="Prove an x402 payment landed on Base (read-only).")
    ap.add_argument("txhash", help="0x-prefixed 64-hex Base transaction hash")
    ap.add_argument("--expect-amount", type=float, default=None,
                    help="minimum USDC that must have reached canonical payTo")
    ap.add_argument("--rpc", default=DEFAULT_RPC, help="Base JSON-RPC endpoint")
    args = ap.parse_args()
    if not TX_RE.match(args.txhash):
        print(json.dumps({"verified": False, "status": "TRANSPORT_ERROR",
                          "error": "txhash must be 0x + 64 hex chars"}, indent=2))
        return 2
    code, result = verify(args.txhash, args.expect_amount, args.rpc)
    print(json.dumps(result, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
