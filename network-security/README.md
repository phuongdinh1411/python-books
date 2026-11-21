# 🔐 Network Protocols & Secure Communication

> Everything a Senior Backend Engineer needs to know about how data moves
> across networks and how to protect it in production systems.
> Built to match the WorldQuant Senior SWE JD: *"solid grasp of network protocols,
> API design, and secure communication implementations"*.

---

## 📂 Structure

| # | Topic | File | Effort |
|---|-------|------|--------|
| 1 | Network Protocols (TCP, HTTP, WebSocket) | [`01-protocols/README.md`](01-protocols/README.md) | 2 days |
| 2 | API Design (REST, gRPC, rate limiting) | [`02-api-design/README.md`](02-api-design/README.md) | 2 days |
| 3 | Secure Communication (TLS, JWT, OAuth) | [`03-secure-communication/README.md`](03-secure-communication/README.md) | 2 days |

**Total: ~1 week part-time**

---

## 🎯 Why This Matters for Senior Roles

The WorldQuant Senior Backend JD says explicitly:

> *"Solid grasp of network protocols, API design, and secure communication implementations"*

This isn't about memorizing RFCs. It's about being able to:
- **Diagnose** production incidents (why is latency high? why are connections dropping?)
- **Design** APIs that are correct, versioned, and paginated at scale
- **Secure** systems against real attack vectors (SSRF, IDOR, token leakage)
- **Answer** interview questions confidently with depth and tradeoffs

---

## 🗺️ Mental Model

```
┌─────────────────────────────────────────────────────────────────────┐
│                    NETWORK KNOWLEDGE MAP                            │
├─────────────────┬───────────────────────────────────────────────────┤
│ PROTOCOLS       │ TCP/IP, UDP, HTTP/1.1, HTTP/2, HTTP/3 (QUIC),     │
│                 │ WebSocket, DNS, TLS 1.2/1.3                        │
├─────────────────┼───────────────────────────────────────────────────┤
│ API DESIGN      │ REST (idempotency, versioning, pagination),        │
│                 │ gRPC (protobuf, streaming), GraphQL, WebHooks,     │
│                 │ Rate limiting (token bucket), API Gateway          │
├─────────────────┼───────────────────────────────────────────────────┤
│ SECURITY        │ TLS handshake, mTLS, JWT, OAuth 2.0,              │
│                 │ OWASP Top 10 (SSRF, IDOR, injection),             │
│                 │ Secrets management (Vault, AWS SSM)                │
└─────────────────┴───────────────────────────────────────────────────┘
```

---

## ⚡ 5-Minute Cheat Sheet

```
TCP   → reliable, ordered, connection-based (HTTP, DB connections)
UDP   → fire-and-forget, faster, unordered (DNS, video, QUIC)
HTTP/1.1 → one request per connection (keep-alive helps)
HTTP/2   → multiplexed streams, header compression, same TCP connection
HTTP/3   → HTTP/2 semantics over QUIC (UDP-based, no head-of-line blocking)
WebSocket → full-duplex over a single TCP connection (real-time)

REST  → stateless, resource-oriented, HTTP verbs
gRPC  → protobuf, strongly typed, streaming, 7x faster than JSON/REST
GraphQL → client specifies exact fields, one endpoint

TLS   → encrypt + authenticate the connection (certificate-based)
mTLS  → both sides present certificates (service-to-service auth)
JWT   → self-contained token (header.payload.signature)
OAuth → delegated authorization (you let GitHub auth you on behalf of a 3rd party)

Token bucket → smooth rate limiting, allows bursts up to bucket capacity
Leaky bucket → strict rate limiting, constant output rate
```
