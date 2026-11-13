# Recipe 04 — MCP: use the fleet from any MCP client

Don't want to hand-roll x402? The RAEN MCP gateway exposes 5 fleet tools over MCP
with Bearer-key auth.

## 1. Get a key (self-serve, 30 days)

```bash
curl -s -X POST https://raen-mcp-gateway.fly.dev/keys/request \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.org"}'
# {"ok":true,"message":"check your email — a verification link is on its way"}
```

Click the verification link in the email — a 30-day Bearer key is issued to that
address. Rate limit: 3 requests/day/IP. (Test domains like `example.com` are rejected
with a clear 400; use a real address.)

## 2. Check what's exposed

```bash
curl -s https://raen-mcp-gateway.fly.dev/health
# {"ok":true,"tools":["raen_law_lookup","raen_ticker_analysis",
#  "raen_dispute_letter","raen_image_generate","raen_contract_analysis"]}
```

The gateway is itself a paid x402 resource: an unauthenticated call to `/mcp` returns
a 402 challenge (that's the gate working, not an error).

## 3. Call a tool

Point any MCP client at `https://raen-mcp-gateway.fly.dev/mcp` with header
`Authorization: Bearer <your-key>`, or call the JSON-RPC endpoint directly:

```bash
curl -s -X POST https://raen-mcp-gateway.fly.dev/mcp \
  -H 'Authorization: Bearer <your-key>' \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call",
       "params":{"name":"raen_law_lookup","arguments":{"topic":"FCRA section 605"}}}'
```

## 4. A2A discovery

Agent-card at `/.well-known/agent.json`:
<https://raen-mcp-gateway.fly.dev/.well-known/agent.json>

Also listed on the MCP Registry as `io.github.bshelby88/raen-mcp`.

Next: [Recipe 05 — dispatch router](05-dispatch-router.md).
