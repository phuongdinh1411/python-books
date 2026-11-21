# Part 1 — Network Protocols

> **Duration:** 2 days | **Priority:** 🔴 Critical
> *"Solid grasp of network protocols"* — WorldQuant Senior Backend JD

---

## 🎯 Learning Objectives

- Trace a request from browser to server: DNS → TCP → TLS → HTTP → response
- Explain TCP vs UDP tradeoffs with real use cases
- Understand what HTTP/2 and HTTP/3 solve and why they exist
- Know when to use WebSockets vs SSE vs long-polling
- Read `netstat`, `tcpdump`, and `ss` output in a production incident

---

## Section 1 — The Full Journey: `GET https://api.example.com/data`

Walk through this end-to-end. Interviewers love this question.

```
1. DNS Resolution
   Browser → OS cache → /etc/hosts → Recursive resolver → Root NS →
   TLD NS (.com) → Authoritative NS → A record: 93.184.216.34
   TTL: DNS result cached for TTL seconds (e.g. 300s = 5 min)
   Tools: dig api.example.com, nslookup api.example.com

2. TCP 3-Way Handshake
   Client → SYN                              → Server
   Client ← SYN-ACK                          ← Server
   Client → ACK                              → Server
   Connection established. 1 RTT overhead.

3. TLS 1.3 Handshake (1 RTT — faster than TLS 1.2's 2 RTT)
   Client → ClientHello (supported ciphers, key_share)   → Server
   Client ← ServerHello (chosen cipher, key_share,
            Certificate, CertificateVerify, Finished)     ← Server
   Client → Finished                                      → Server
   Encrypted channel established. 1 RTT overhead.
   (TLS 1.3 0-RTT resumption: 0 extra RTT for reconnects)

4. HTTP Request
   GET /data HTTP/1.1
   Host: api.example.com
   Authorization: Bearer eyJhb...
   Accept: application/json

5. Server Processing
   Load balancer → picks healthy backend → routes request
   Backend: auth check → DB query → serialize → response

6. HTTP Response
   HTTP/1.1 200 OK
   Content-Type: application/json
   Cache-Control: max-age=60
   {"data": [...]}

7. TCP Teardown (4-Way)
   Client → FIN    → Server
   Client ← ACK    ← Server
   Client ← FIN    ← Server
   Client → ACK    → Server
   (TIME_WAIT: client waits 2×MSL before fully closing — avoids stale packets)
```

---

## Section 2 — TCP vs UDP

### TCP — Transmission Control Protocol

```
Guarantees:
  ✅ Delivery (retransmits lost packets)
  ✅ Order (reassembles out-of-order packets)
  ✅ No duplication
  ✅ Flow control (receiver advertises window size)
  ✅ Congestion control (slow start, AIMD)

Cost:
  ❌ 3-way handshake overhead (1 RTT before data)
  ❌ Head-of-line blocking: one lost packet stalls the entire stream
  ❌ Higher latency (retransmit + ACK cycle)

Use for: HTTP, HTTPS, database connections, SSH, SMTP
         Any protocol where reliability matters more than latency
```

### UDP — User Datagram Protocol

```
Guarantees:
  ❌ No delivery guarantee
  ❌ No ordering
  ❌ No flow control

Advantages:
  ✅ No handshake overhead
  ✅ No head-of-line blocking
  ✅ Lower latency (fire and forget)
  ✅ Multicast support

Use for:
  - DNS (single req/resp, fast, app can retry)
  - Video/audio streaming (stale frame < no frame)
  - Online gaming (latency > reliability)
  - QUIC / HTTP/3 (UDP + reliability in app layer)
  - Market data multicast (tick feeds to many consumers simultaneously)
```

### Financial Systems: When UDP Makes Sense

```
Market data feed (NYSE, CME):
  - Exchanges broadcast tick data via UDP multicast
  - 1M+ msgs/sec to thousands of receivers simultaneously
  - A missed tick is recovered from: retransmit channel (separate TCP)
  - Latency matters more than 100% delivery

Low-latency trading:
  - UDP kernel bypass (DPDK, RDMA) for < 1μs latency
  - TCP has ~10μs overhead from OS network stack
  - For HFT: kernel bypass UDP saves 10+ microseconds per message

Control plane (REST API, DB): always TCP
Data plane (market data): often UDP multicast
```

### TCP Flow Control and Congestion Control

```
Flow Control (receiver-based):
  Receiver advertises window size (how much buffer it has)
  Sender never sends more than the window
  Window shrinks as receiver buffer fills: backpressure!
  Window = 0: sender stops until receiver acknowledges

Congestion Control (network-based):
  Slow Start: begin with small congestion window, double each RTT
  AIMD: Additive Increase (add 1 each RTT), Multiplicative Decrease (halve on loss)
  Cubic (Linux default): faster ramp-up for high-bandwidth paths

Why this matters for backend engineers:
  - TCP buffer sizing: SO_RCVBUF, SO_SNDBUF (tune for high-throughput services)
  - Nagle algorithm: batches small packets (TCP_NODELAY disables it — use for latency-sensitive APIs)
  - TIME_WAIT accumulation: many short-lived connections → SO_REUSEADDR, connection pooling
```

---

## Section 3 — HTTP Versions

### HTTP/1.1

```
Problems:
  - One request per TCP connection at a time (without pipelining)
  - Head-of-line blocking: second request waits for first to complete
  - Browsers open 6 parallel connections per domain to work around this

Improvements over HTTP/1.0:
  - keep-alive: reuse TCP connection for multiple requests
  - Chunked transfer encoding
  - Host header (virtual hosting)
  - Range requests

Headers are plaintext: large, uncompressed overhead
```

### HTTP/2

```
Key improvements:
  ✅ Multiplexing: many requests over ONE TCP connection, interleaved
  ✅ Header compression (HPACK): 60–90% header size reduction
  ✅ Server push: server sends resources before client asks
  ✅ Binary framing (not text) — more efficient to parse

Still has:
  ❌ TCP head-of-line blocking: one lost TCP packet stalls ALL streams
     (because TCP guarantees ordering — all streams share one TCP stream)

When HTTP/2 helps:
  - APIs with many small requests (high header overhead)
  - Browsers loading many assets (images, scripts)
  - Services with high connection overhead (TLS handshake is expensive)
```

### HTTP/3 (QUIC)

```
Built on UDP instead of TCP:
  ✅ No TCP head-of-line blocking (each QUIC stream is independent)
  ✅ 0-RTT connection establishment for reconnects (faster than TLS 1.3)
  ✅ Connection migration (phone switches WiFi → 4G, connection survives)
  ✅ Built-in encryption (QUIC always encrypted, unlike TCP)

QUIC implements reliability at the application level (not OS):
  - Each stream has independent ordering and retransmit
  - Lost packet in stream A does not block stream B

Real-world: Google uses QUIC for all its services; ~25% of web traffic is HTTP/3

Backend implications:
  - Most servers support HTTP/3 behind a CDN (Cloudflare, Fastly)
  - gRPC-over-HTTP/3 is coming (currently gRPC uses HTTP/2)
  - For internal microservices: HTTP/2 is still the standard
```

### HTTP Methods: Idempotency and Safety

```
Safe     = does not modify state (can be cached, logged, retried freely)
Idempotent = calling N times = same result as calling once

Method    Safe?    Idempotent?    Use for
GET       ✅       ✅             Retrieve resource
HEAD      ✅       ✅             Same as GET, headers only
OPTIONS   ✅       ✅             CORS preflight, capability check
DELETE    ❌       ✅             Delete resource (delete twice = still deleted)
PUT       ❌       ✅             Replace full resource
PATCH     ❌       ❌ (usually)   Partial update (depends on implementation)
POST      ❌       ❌             Create resource or submit action

Interview trap: DELETE is idempotent (second call returns 404 but state is same)
Interview trap: PUT is idempotent but POST is not
```

---

## Section 4 — DNS Deep Dive

```
Resolution chain:
  Browser cache → OS cache (/etc/hosts) → Stub resolver →
  Recursive resolver (ISP or 8.8.8.8) → Root nameserver (.) →
  TLD nameserver (.com) → Authoritative nameserver →
  A record (IPv4) or AAAA record (IPv6)

Record types:
  A     → hostname → IPv4 address
  AAAA  → hostname → IPv6 address
  CNAME → alias → canonical name (api.example.com → lb.example.com)
  MX    → mail server for domain
  TXT   → arbitrary text (SPF, DKIM, domain verification)
  NS    → nameservers responsible for domain
  SRV   → service location (_grpc._tcp.example.com → host:port)

TTL: how long resolvers cache the result
  High TTL (3600s): fewer DNS queries, but slow to propagate changes
  Low TTL (60s): fast failover / traffic migration, but more queries

DNS and load balancing:
  Round-robin DNS: return multiple A records, client picks one
  GeoDNS: return nearest server based on client IP
  Weighted DNS: return different IPs at different frequencies

Failure scenario: DNS poisoning (cache poisoning)
  Attack: inject fake A record → user directed to attacker's server
  Defense: DNSSEC (signs records), HTTPS (certificate validates domain)

Practical:
  $ dig api.example.com          # full DNS trace
  $ dig +short api.example.com   # just the IP
  $ dig api.example.com @8.8.8.8 # use Google's resolver
  $ nslookup api.example.com
```

---

## Section 5 — WebSockets, SSE, and Long-Polling

### When to Use Each

```
                    Server-sent   Client-sent   Protocol overhead   Persistence
HTTP polling        YES (pull)    per-poll      HIGH (new TCP each)  NO
Long-polling        YES (delayed) per-poll      MEDIUM               NO
SSE                 YES           NO            LOW (one HTTP conn)  YES
WebSocket           YES           YES           LOWEST (one TCP conn) YES

Decision tree:
  One-way server→client only:   SSE (simpler, works with HTTP/2 multiplexing)
  Bidirectional real-time:       WebSocket
  Infrequent updates, simple:    Long-polling (easiest to implement + debug)
  Existing HTTP/2 infra:         SSE (multiplexed over same connection for free)
```

### Long-Polling

```python
# Server holds the request open until data is available
@app.get("/updates")
async def long_poll(last_id: int, timeout: float = 30):
    """Return when new data arrives or after timeout."""
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        new_data = await db.fetch_since(last_id)
        if new_data:
            return new_data
        await asyncio.sleep(0.5)
    return []  # timeout — client reconnects immediately

# Client: immediately reconnects after each response
# Effectively a "pushed" response with HTTP semantics
# Downside: each "push" is a full HTTP req/resp cycle
```

### Server-Sent Events (SSE)

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import asyncio

@app.get("/stream/prices")
async def stream_prices(symbol: str):
    """Push price updates as they arrive."""
    async def event_generator():
        async for price in subscribe_to_prices(symbol):
            # SSE format: "data: <payload>\n\n"
            yield f"data: {json.dumps(price)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",   # disable Nginx buffering!
        }
    )

# Client (JavaScript):
# const es = new EventSource('/stream/prices?symbol=AAPL');
# es.onmessage = e => console.log(JSON.parse(e.data));
# es.onerror   = e => setTimeout(() => reconnect(), 3000); // auto-reconnect
```

### WebSocket

```python
from fastapi import WebSocket, WebSocketDisconnect

@app.websocket("/ws/market")
async def market_websocket(ws: WebSocket, token: str):
    # Auth before accepting
    user = verify_token(token)
    if not user:
        await ws.close(code=4001)
        return
    
    await ws.accept()
    
    try:
        # Send initial snapshot
        await ws.send_json({"type": "snapshot", "data": await get_snapshot()})
        
        # Bidirectional: receive subscriptions, send updates
        async with asyncio.TaskGroup() as tg:
            tg.create_task(_receive_subscriptions(ws, user))
            tg.create_task(_send_updates(ws, user))
    
    except WebSocketDisconnect:
        cleanup(user)

async def _receive_subscriptions(ws: WebSocket, user):
    async for msg in ws.iter_json():
        if msg["type"] == "subscribe":
            user.subscriptions.add(msg["symbol"])

async def _send_updates(ws: WebSocket, user):
    async for update in price_feed():
        if update["symbol"] in user.subscriptions:
            await ws.send_json(update)
```

---

## Section 6 — The OSI Model (What Backend Engineers Actually Need)

```
Layer 7  Application  HTTP, gRPC, WebSocket, DNS, SMTP, FTP
Layer 6  Presentation  TLS/SSL, encoding (JSON, Protobuf)
Layer 5  Session  (mostly handled by layer 7 in practice)
Layer 4  Transport  TCP, UDP — ports, reliability, flow control
Layer 3  Network  IP — routing, addressing, packets
Layer 2  Data Link  Ethernet, Wi-Fi — frames, MAC addresses
Layer 1  Physical  Cables, radio waves

What you actually need to know:
  L7 (Application): where your code lives — HTTP headers, gRPC metadata
  L4 (Transport): TCP/UDP — ports, connections, reliability
  L3 (Network): IP — routing, NAT, subnets
  L2/L1: usually handled by infra, but relevant for latency-sensitive trading systems

Interview shortcut: "I work primarily at L7 (application) and L4 (transport),
  with awareness of L3 for routing/NAT/firewall debugging"

Common debugging:
  curl -v https://api.example.com    # L7 (HTTP)
  telnet api.example.com 443         # L4 (TCP connectivity)
  ping api.example.com               # L3 (ICMP reachability)
  traceroute api.example.com         # L3 (routing path)
  netstat -an | grep ESTABLISHED     # L4 (open connections)
  ss -tlnp                           # L4 (listening ports)
  tcpdump -i eth0 port 443           # L4 (raw packets)
```

---

## 🏋️ Exercises

### Exercise 1 — Trace a Slow Request
Given: an API endpoint takes 800ms instead of 50ms.
Walk through how you'd diagnose: DNS? TCP handshake? TLS? Server processing? DB?
Tools: `curl -w "@curl-format.txt"`, `tcpdump`, application traces.

### Exercise 2 — TCP Connection Pooling
Write a Python script that:
- Makes 100 HTTP requests WITHOUT connection pooling → measure time
- Makes 100 HTTP requests WITH `httpx.Client` (connection pool) → measure time
- Explain the difference in terms of TCP handshakes saved

### Exercise 3 — WebSocket vs SSE Decision
For each scenario, choose WebSocket or SSE and explain why:
1. Live stock ticker (server pushes prices to a dashboard)
2. Collaborative code editor (multiple users edit simultaneously)
3. Real-time log streaming from a running job
4. Chat application

---

## ✅ Self-Check Questions

1. What happens between typing a URL and seeing the first byte of response?
2. When would you choose UDP over TCP in a financial system?
3. What problem does HTTP/2 multiplexing solve? What problem does it NOT solve?
4. What is HTTP/3 / QUIC and what does it fix that HTTP/2 couldn't?
5. Which HTTP methods are idempotent? Which are safe?
6. What is the difference between WebSocket and SSE? When would you pick each?
7. What is DNS TTL and what is the tradeoff of setting it very low vs very high?
8. What is TCP head-of-line blocking?
9. What does `TCP_NODELAY` do and when would you set it?
10. At which OSI layer does TLS operate?

---

## 🔗 Key Links

- https://hpbn.co/ — High Performance Browser Networking (free book, excellent)
- https://www.cloudflare.com/learning/ddos/glossary/tcp-ip/ — TCP/IP explained
- https://http3-explained.haxx.se/ — HTTP/3 explained (free ebook)
- https://developer.mozilla.org/en-US/docs/Web/HTTP/Overview — HTTP overview
