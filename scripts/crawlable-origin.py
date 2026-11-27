#!/usr/bin/env python3
"""Crawlable API Origin Card — recipe 47.

Turn a LIVE-decoded x402 offer set into a static, crawler-readable homepage for
API-only origins. Root cause fixed: 402registry/402index-style crawlers grade an
origin whose `/` returns 404 as 'no crawlable homepage' (contract-eye and
dispute-forge were refused, score 18), so the origin is invisible to the buyer
discovery path even though its paid route is healthy.

Read-only. Sends at most one UNPAID probe to a public paid route to decode the
402. Never signs, never sends X-PAYMENT, holds no keys, moves no funds.

Safety: accepts[] must carry the FULL canonical payTo (case-insensitive,
homoglyph-safe), network eip155:8453, scheme exact and a positive integer
amount. Any drift -> FAIL_DRIFT, no page is written.
"""
import argparse, base64, html, json, sys, urllib.request, urllib.error
from html.parser import HTMLParser

CANONICAL_PAYTO_FULL = "0x9b8a27e03ceba490953cda8ab1291c0e13baf72f".lower()
USDC_BASE = "0x833589fcd6edb6e08f4c7c32d4f71b54bdA02913".lower()
NETWORK = "eip155:8453"
SCHEME = "exact"
UA = "Mozilla/5.0 (compatible; RAEN-CrawlableOrigin/1.0; +https://bshelby88.github.io/x402-cookbook/)"


def probe(url, method="POST", body=None, timeout=20):
    """Unpaid probe. Return decoded x402 challenge dict, or raise."""
    data = body.encode() if body else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"User-Agent": UA, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8", "replace")
            hdr = r.headers.get("payment-required") or r.headers.get("x-payment-required")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        hdr = e.headers.get("payment-required") or e.headers.get("x-payment-required")
    if hdr:
        return json.loads(base64.b64decode(hdr + "=" * (-len(hdr) % 4)))
    try:
        d = json.loads(raw)
        if "accepts" in d:
            return d
    except Exception:
        pass
    raise RuntimeError("no decodable 402 challenge (payment-required header or accepts[] body)")


def check_accept(a):
    """Return list of drift findings for one accept[] entry (empty = canonical)."""
    f = []
    payto = str(a.get("payTo", ""))
    if payto.lower() != CANONICAL_PAYTO_FULL:
        f.append("payTo not full canonical (got %s...)" % (payto[:10] + "..." if payto else "EMPTY"))
    if str(a.get("network", "")) != NETWORK:
        f.append("network != %s" % NETWORK)
    if str(a.get("scheme", "")) != SCHEME:
        f.append("scheme != %s" % SCHEME)
    if str(a.get("asset", "")).lower() != USDC_BASE:
        f.append("asset != USDC Base")
    amt = a.get("amount")
    try:
        if int(amt) <= 0:
            raise ValueError
    except Exception:
        f.append("amount not a positive integer")
    return f


def build_page(spec):
    """spec = {name, origin, description, generated_utc, offers:[{method,path,price_usd,summary,challenge}]}"""
    findings = []
    clean = []
    for o in spec.get("offers", []):
        ch = o.get("challenge") or {}
        acc = (ch.get("accepts") or [{}])[0]
        df = check_accept(acc)
        if df:
            findings.append("%s %s: %s" % (o.get("method"), o.get("path"), ", ".join(df)))
        else:
            clean.append(o)
    if findings:
        return None, findings
    if not clean:
        return None, ["no canonical offers to publish"]

    name = html.escape(spec.get("name") or spec.get("origin", "x402 API"))
    origin = html.escape(spec.get("origin", ""))
    desc = html.escape(spec.get("description", ""))
    gen = html.escape(spec.get("generated_utc", ""))

    ld_offers = []
    rows = []
    for o in clean:
        acc = o["challenge"]["accepts"][0]
        atoms = int(acc["amount"])
        price = o.get("price_usd") or ("%.6f" % (atoms / 1e6)).rstrip("0").rstrip(".")
        url = "https://%s%s" % (spec.get("origin", ""), o.get("path", ""))
        ld_offers.append({
            "@type": "Offer",
            "price": str(price),
            "priceCurrency": "USD",
            "url": url,
            "x402": {"scheme": SCHEME, "network": NETWORK, "asset": acc["asset"],
                     "payTo": acc["payTo"], "amount": acc["amount"],
                     "method": o.get("method"), "path": o.get("path")},
        })
        rows.append("<tr><td><code>%s</code></td><td><code>%s</code></td><td>$%s</td><td>%s</td></tr>" % (
            html.escape(str(o.get("method"))), html.escape(str(o.get("path"))),
            html.escape(str(price)), html.escape(str(o.get("summary", "")))))
    ld = {"@context": "https://schema.org", "@type": "WebAPI", "name": name,
          "description": desc, "documentationUrl": "https://bshelby88.github.io/x402-cookbook/",
          "offers": ld_offers}
    ld_s = json.dumps(ld, indent=2)

    doc = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="index,follow">
<title>%(name)s — x402 API</title>
<meta name="description" content="%(desc)s">
<script type="application/ld+json">
%(ld)s
</script>
<style>body{font:16px/1.5 system-ui,sans-serif;max-width:820px;margin:2rem auto;padding:0 1rem;color:#111}
code{background:#f2f4f7;padding:.1rem .3rem;border-radius:3px}table{border-collapse:collapse;width:100%%}
td,th{border:1px solid #ddd;padding:.5rem;text-align:left}footer{margin-top:2rem;color:#555;font-size:.9rem}</style>
</head>
<body>
<h1>%(name)s</h1>
<p>%(desc)s</p>
<h2>Paid endpoints</h2>
<table><thead><tr><th>Method</th><th>Path</th><th>Price</th><th>What it does</th></tr></thead>
<tbody>
%(rows)s
</tbody></table>
<h2>Machine-readable discovery</h2>
<ul>
<li><a href="/.well-known/x402.json">x402.json</a> — canonical manifest</li>
<li><a href="/.well-known/agent-card.json">agent-card.json</a> — A2A agent card</li>
<li><a href="/llms.txt">llms.txt</a> — LLM discovery</li>
<li><a href="https://settlement-collector.fly.dev/stats">settlement telemetry</a> — public, unedited</li>
</ul>
<h2>How to buy</h2>
<p>Send an unpaid request to a paid endpoint. The HTTP <code>402</code> response carries a
base64 <code>payment-required</code> header; decode <code>accepts[]</code> for
<code>scheme=exact</code>, <code>network=eip155:8453</code>, asset USDC (Base) and the canonical
<code>payTo</code>. Settle on-chain with EIP-3009 <code>transferWithAuthorization</code>, then resend
the same request with <code>x-payment</code>. The live 402 challenge is authoritative over any
published snapshot.</p>
<footer>Generated %(gen)s from live 402 decodes. Prices and payTo are read, never hand-typed.
Canonical payTo guard: %(payto)s. External revenue is reported honestly (currently $0.00).</footer>
</body>
</html>
""" % {"name": name, "desc": desc, "ld": ld_s, "rows": "\n".join(rows), "gen": gen,
       "payto": html.escape(CANONICAL_PAYTO_FULL)}
    return doc, []


class _Check(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ld = []
        self._in_ld = False
        self.h1 = False
        self.meta_desc = False
        self.robots = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "h1":
            self.h1 = True
        if tag == "meta" and a.get("name") == "description":
            self.meta_desc = True
        if tag == "meta" and a.get("name") == "robots" and "index" in (a.get("content") or ""):
            self.robots = True
        if tag == "script" and a.get("type") == "application/ld+json":
            self._in_ld = True

    def handle_endtag(self, tag):
        if tag == "script":
            self._in_ld = False

    def handle_data(self, data):
        if self._in_ld:
            self.ld.append(data)


def validate_page(page, spec):
    """Return (verdict, findings). CI-grade: fails on canonical drift, not on style."""
    p = _Check()
    p.feed(page)
    f = []
    if not p.h1:
        f.append("no <h1> (crawlers need a semantic heading)")
    if not p.meta_desc:
        f.append("no meta description")
    if not p.robots:
        f.append("no index,follow robots meta")
    if not p.ld:
        f.append("no JSON-LD block")
    else:
        try:
            ld = json.loads("".join(p.ld))
            if ld.get("@type") != "WebAPI":
                f.append("JSON-LD @type != WebAPI")
            offers = ld.get("offers", [])
            if not offers:
                f.append("JSON-LD has no offers")
            for o in offers:
                df = check_accept(o.get("x402", {}))
                if df:
                    f.append("JSON-LD offer drift: " + ", ".join(df))
            if CANONICAL_PAYTO_FULL not in page.lower():
                f.append("canonical payTo not present in page")
        except Exception as e:
            f.append("JSON-LD parse failed: %s" % str(e)[:60])
    drift = any(("drift" in x.lower()) or ("not present" in x) or ("not full canonical" in x)
                or ("!=" in x) for x in f)
    return ("FAIL_DRIFT" if drift else ("FAIL" if f else "CANONICAL")), f


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--spec", help="spec JSON file (name, origin, description, offers[] with challenge)")
    ap.add_argument("--probe", help="URL to probe unpaid for a live 402 (writes a spec challenge into offer[0])")
    ap.add_argument("--method", default="POST")
    ap.add_argument("--body", default=None)
    ap.add_argument("--out", help="write generated HTML here")
    ap.add_argument("--check", help="validate an existing HTML file against --spec")
    a = ap.parse_args()
    if not a.spec:
        ap.error("--spec is required")
    spec = json.load(open(a.spec, encoding="utf-8"))
    if a.probe:
        ch = probe(a.probe, a.method, a.body)
        if not spec.get("offers"):
            spec["offers"] = [{"method": a.method, "path": "/", "summary": spec.get("description", "")}]
        spec["offers"][0]["challenge"] = ch
        with open(a.spec, "w", encoding="utf-8") as fh:
            json.dump(spec, fh, indent=2)
        acc = (ch.get("accepts") or [{}])[0]
        print("PROBE_OK method=%s atoms=%s payTo=%s" % (a.method, acc.get("amount"), acc.get("payTo")))
        return 0
    if a.check:
        page = open(a.check, encoding="utf-8").read()
        verdict, f = validate_page(page, spec)
        print("VERDICT", verdict)
        for x in f:
            print(" -", x)
        return 1 if verdict != "CANONICAL" else 0
    page, f = build_page(spec)
    if f or page is None:
        print("FAIL_DRIFT — no page generated")
        for x in f:
            print(" -", x)
        return 2
    assert page is not None
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(page)
        print("WROTE", a.out, len(page), "bytes")
    else:
        sys.stdout.write(page)
    verdict, f = validate_page(page, spec)
    print("VERDICT", verdict, "offers", len(spec.get("offers", [])), file=sys.stderr)
    for x in f:
        print(" -", x, file=sys.stderr)
    return 0 if verdict == "CANONICAL" else 1


if __name__ == "__main__":
    from html.parser import HTMLParser
    sys.exit(main())
