# Part 3 — Secure Communication

> **Duration:** 2 days | **Priority:** 🔴 Critical
> *"Secure communication implementations"* — WorldQuant Senior Backend JD

---

## 🎯 Learning Objectives

- Explain the TLS 1.3 handshake and what changed from 1.2
- Design mTLS for service-to-service authentication
- Implement JWT correctly — including the attack vectors to avoid
- Know OAuth 2.0 flows and when to use each
- Defend against OWASP Top 10 API vulnerabilities
- Manage secrets correctly in production (never hardcode)

---

## Section 1 — TLS: How the Encrypted Channel Is Established

### TLS 1.3 Handshake (1 RTT)

```
Client                                           Server
  │                                                │
  │── ClientHello ──────────────────────────────► │
  │   - TLS version: 1.3                           │
  │   - Supported cipher suites                    │
  │   - key_share (Diffie-Hellman public key)      │
  │   - Random nonce                               │
  │                                                │
  │ ◄── ServerHello ────────────────────────────── │
  │     - Chosen cipher suite                      │
  │     - key_share (server DH public key)         │
  │     - Certificate (server's identity)          │
  │     - CertificateVerify (signature)            │
  │     - Finished (MAC of handshake)              │
  │                                                │
  │── Finished ──────────────────────────────────► │
  │                                                │
  │════════ Encrypted Application Data ═══════════│

Total: 1 RTT before first byte of data

TLS 1.2 required 2 RTTs (slower by 1 RTT ≈ 20–50ms)
TLS 1.3 0-RTT: for reconnecting clients, 0 extra RTT (data sent with Finished)
  → Security note: 0-RTT is replay-vulnerable — only use for idempotent requests
```

### What TLS Provides

```
Confidentiality: data is encrypted (AES-GCM, ChaCha20)
  → Even if attacker intercepts packets, they see ciphertext only

Integrity: data cannot be modified in transit without detection (HMAC/AEAD)
  → Any bit flip in ciphertext → decryption fails → error

Authentication: server identity verified via certificate
  → Certificate issued by trusted CA, signed with server's private key
  → Client verifies: certificate is valid, not expired, issued for correct domain

NOT provided by TLS alone:
  ✗ Client authentication (client is anonymous unless mTLS is used)
  ✗ Protection against compromised server (server has the plaintext)
  ✗ Protection if certificate authority is compromised
```

### Certificate Hierarchy

```
Root CA (self-signed, pre-installed in OS/browser trust store)
  ↓ signs
Intermediate CA (issued by Root CA)
  ↓ signs
Server Certificate (issued for api.example.com)

Verification chain (client does this automatically):
  1. Is the server cert signed by an Intermediate CA I trust?
  2. Is that Intermediate CA signed by a Root CA in my trust store?
  3. Is the cert's CN/SAN matching the domain I requested?
  4. Is the cert within its validity period (not expired)?
  5. Is the cert revoked? (OCSP stapling)

Tools:
  openssl s_client -connect api.example.com:443    # inspect cert
  openssl x509 -in cert.pem -text -noout          # decode a cert
  curl -v --cert client.pem --key key.pem ...      # client cert (mTLS)
```

### TLS in Python

```python
import ssl
import httpx

# HTTPS client (verify server cert — always do this in production)
client = httpx.Client(verify=True)  # True = use system trust store

# Custom CA (internal services with private CA)
client = httpx.Client(verify="/path/to/internal-ca.pem")

# mTLS client (present client certificate)
client = httpx.Client(
    cert=("/path/to/client.pem", "/path/to/client.key"),
    verify="/path/to/server-ca.pem",
)

# NEVER in production:
client = httpx.Client(verify=False)  # disables all certificate verification!
```

---

## Section 2 — mTLS: Mutual TLS

### What mTLS Adds

```
Standard TLS: only the server presents a certificate
  → Client verifies the server is who it claims to be
  → Server has NO idea who the client is (anonymous)

mTLS: BOTH sides present certificates
  → Client verifies server ✅ (same as TLS)
  → Server verifies client ✅ (client must present a trusted cert)

Use cases:
  ✅ Service-to-service auth in microservices (no API keys needed)
  ✅ Internal APIs that must not be accessible from outside
  ✅ Zero-trust architecture (every service proves its identity)
  ✅ Hardware/IoT devices calling a backend (device cert embedded)

Tools:
  Service mesh: Istio, Linkerd (auto-inject mTLS between services)
  DIY: generate client certs with internal CA, verify in nginx/app
```

### Setting Up mTLS

```bash
# 1. Create internal CA
openssl genrsa -out ca.key 4096
openssl req -new -x509 -days 1825 -key ca.key -out ca.pem \
    -subj "/O=WorldQuant/CN=Internal CA"

# 2. Create server certificate (signed by internal CA)
openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr -subj "/CN=api.internal"
openssl x509 -req -days 365 -in server.csr -CA ca.pem -CAkey ca.key \
    -CAcreateserial -out server.pem

# 3. Create client certificate (for each service)
openssl genrsa -out worker-service.key 2048
openssl req -new -key worker-service.key -out worker.csr \
    -subj "/CN=worker-service/O=WorldQuant"
openssl x509 -req -days 365 -in worker.csr -CA ca.pem -CAkey ca.key \
    -CAcreateserial -out worker-service.pem
```

```python
# Server: require client certificate
import ssl
from fastapi import FastAPI
import uvicorn

ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ssl_context.load_cert_chain("/certs/server.pem", "/certs/server.key")
ssl_context.load_verify_locations("/certs/ca.pem")
ssl_context.verify_mode = ssl.CERT_REQUIRED   # reject clients without cert!

uvicorn.run(app, ssl=ssl_context, host="0.0.0.0", port=8443)

# Or via nginx (simpler — terminate mTLS at proxy):
# ssl_client_certificate /etc/nginx/certs/ca.pem;
# ssl_verify_client on;
# → nginx passes verified client CN in header: X-Client-Cert-Subject

# Extract identity from cert in FastAPI
from fastapi import Request

@app.get("/internal/data")
async def internal_data(request: Request):
    # nginx sets this after verifying client cert
    client_cn = request.headers.get("X-Client-Cert-Subject")
    if not client_cn or "worker-service" not in client_cn:
        raise HTTPException(403, "Unknown client service")
    return {"data": "sensitive internal data"}
```

---

## Section 3 — JWT: JSON Web Tokens

### JWT Structure

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9    ← Header (base64)
.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6Ikpva G4iLCJpYXQiOjE2MDAwMDAwMDB9  ← Payload (base64)
.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c  ← Signature (base64)

Header: { "alg": "HS256", "typ": "JWT" }
Payload: {
    "sub": "user_123",          # Subject (who the token is about)
    "iss": "api.example.com",   # Issuer (who created it)
    "aud": "api.example.com",   # Audience (who it's for)
    "iat": 1700000000,          # Issued At (Unix timestamp)
    "exp": 1700003600,          # Expiry (Unix timestamp — always set this!)
    "roles": ["researcher"],    # Custom claims
}
Signature: HMAC-SHA256(base64(header) + "." + base64(payload), secret)
```

### Correct JWT Implementation

```python
import jwt
from datetime import datetime, timedelta, timezone
from typing import Literal

SECRET_KEY = "from-vault-not-hardcoded"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE = timedelta(minutes=15)
REFRESH_TOKEN_EXPIRE = timedelta(days=7)

def create_token(
    user_id: int,
    token_type: Literal["access", "refresh"],
    extra_claims: dict | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    expire = now + (ACCESS_TOKEN_EXPIRE if token_type == "access" else REFRESH_TOKEN_EXPIRE)
    payload = {
        "sub": str(user_id),
        "type": token_type,
        "iat": now,
        "exp": expire,
        "iss": "api.example.com",          # always set issuer
        "aud": "api.example.com",          # always set audience
        **(extra_claims or {}),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str, expected_type: str = "access") -> dict:
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={
                "require": ["exp", "iat", "sub", "iss", "aud"],  # enforce required claims
            },
            issuer="api.example.com",
            audience="api.example.com",
        )
    except jwt.ExpiredSignatureError:
        raise ValueError("Token expired")
    except jwt.InvalidTokenError as e:
        raise ValueError(f"Invalid token: {e}")

    if payload.get("type") != expected_type:
        raise ValueError(f"Wrong token type: expected {expected_type}")

    return payload
```

### JWT Attacks and Defenses

```
Attack 1: alg=none
  Attacker changes header to {"alg": "none"} and removes signature
  Defense: ALWAYS specify allowed algorithms in jwt.decode(algorithms=["HS256"])
           NEVER accept alg=none

Attack 2: HS256 / RS256 confusion
  If server uses RS256 (asymmetric), attacker changes to HS256 and
  signs with the PUBLIC key (which they have)
  Defense: explicitly specify algorithm, never infer from token header

Attack 3: weak secret
  For HS256, brute-force the secret if it's short/guessable
  Defense: use 256-bit random secret: python -c "import secrets; print(secrets.token_hex(32))"

Attack 4: token theft (XSS)
  Token in localStorage → JavaScript can read it → XSS attack steals token
  Defense: store access token in memory (variable), refresh token in httpOnly cookie

Attack 5: JWT stored in URL
  Token in ?token=... → logged in server logs, browser history
  Defense: always use Authorization: Bearer header

Attack 6: no expiry
  Token valid forever → one stolen token = permanent access
  Defense: short access tokens (15 min), longer refresh tokens (7 days)
           refresh token rotation: each refresh returns a new refresh token
```

### Access + Refresh Token Pattern

```python
# Access token: short-lived (15 min), sent in Authorization header
# Refresh token: long-lived (7 days), stored in httpOnly cookie, used to get new access tokens

@app.post("/auth/login")
async def login(credentials: LoginRequest, response: Response) -> dict:
    user = await authenticate(credentials)
    access = create_token(user.id, "access")
    refresh = create_token(user.id, "refresh")

    # Refresh token in httpOnly cookie (JS cannot read it)
    response.set_cookie(
        "refresh_token", refresh,
        httponly=True,    # no JS access
        secure=True,      # HTTPS only
        samesite="strict", # no cross-origin
        max_age=7 * 24 * 3600,
    )
    return {"access_token": access}  # access token in response body → store in memory


@app.post("/auth/refresh")
async def refresh(request: Request) -> dict:
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(401, "No refresh token")
    payload = verify_token(refresh_token, expected_type="refresh")
    # Rotate: issue new refresh token (old one is invalidated)
    new_access = create_token(int(payload["sub"]), "access")
    return {"access_token": new_access}
```

---

## Section 4 — OAuth 2.0

### Core Concept: Delegated Authorization

```
Problem: User wants to let App B access their data on Service A
         WITHOUT giving App B their Service A password

OAuth 2.0 solution:
  User grants App B limited access to Service A, without sharing credentials
  Service A issues App B a token with specific scopes

Roles:
  Resource Owner   = User (owns the data)
  Resource Server  = Service A (has the data: GitHub, Google, etc.)
  Client           = App B (wants access to data)
  Authorization Server = issues tokens (often same as Resource Server)
```

### Authorization Code Flow (for user-facing apps)

```
1. App B redirects User to Service A's login:
   GET https://github.com/login/oauth/authorize
       ?client_id=abc
       &redirect_uri=https://app-b.com/callback
       &scope=read:user,repo
       &state=random_csrf_token    ← MUST include to prevent CSRF
       &code_challenge=...         ← PKCE (for public clients)

2. User logs in to GitHub, grants permission

3. GitHub redirects back to App B:
   GET https://app-b.com/callback?code=xyz&state=random_csrf_token

4. App B exchanges code for token (server-to-server, secret included):
   POST https://github.com/login/oauth/access_token
   {code: xyz, client_id: abc, client_secret: SECRET, redirect_uri: ...}

5. GitHub returns: {"access_token": "gho_...", "scope": "read:user,repo"}

6. App B uses token to call GitHub API:
   GET https://api.github.com/user
   Authorization: Bearer gho_...
```

### Client Credentials Flow (for service-to-service)

```python
# No user involved — machine-to-machine authentication
# Service authenticates with its own client_id + client_secret

import httpx

async def get_service_token(
    auth_server_url: str,
    client_id: str,
    client_secret: str,
    scope: str = "read:signals",
) -> str:
    """Get an access token for this service (not on behalf of a user)."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{auth_server_url}/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": scope,
            },
        )
        response.raise_for_status()
        return response.json()["access_token"]

# Token caching (don't fetch a new token on every request):
from functools import lru_cache

_token_cache: dict = {}

async def get_cached_token() -> str:
    global _token_cache
    if _token_cache.get("expires_at", 0) > time.time() + 60:  # refresh 60s before expiry
        return _token_cache["token"]
    token_data = await fetch_token_from_auth_server()
    _token_cache = {
        "token": token_data["access_token"],
        "expires_at": time.time() + token_data["expires_in"],
    }
    return _token_cache["token"]
```

### OAuth Flows Summary

| Flow | Use when | Example |
|------|----------|---------|
| Authorization Code + PKCE | Web/mobile app acting on behalf of user | "Login with Google" |
| Client Credentials | Service-to-service (no user) | Backend calling an API |
| Device Code | Input-constrained devices (TV, CLI) | `gh auth login` in terminal |
| Implicit | ⚠️ Deprecated — tokens in URL fragment | (don't use) |
| Password | ⚠️ Deprecated — user sends password to client | (don't use) |

---

## Section 5 — OWASP API Security Top 10

> These are the most common real-world API vulnerabilities. Know them cold.

### 1. Broken Object Level Authorization (BOLA / IDOR)

```python
# INSECURE: trusting user-provided ID without ownership check
@app.get("/orders/{order_id}")
async def get_order(order_id: int, user_id: int = Depends(get_current_user)):
    return await db.fetch("SELECT * FROM orders WHERE id = $1", order_id)
    # Attacker changes order_id=123 → order_id=456 → reads another user's order!

# SECURE: always verify ownership
@app.get("/orders/{order_id}")
async def get_order(order_id: int, user_id: int = Depends(get_current_user)):
    order = await db.fetchrow(
        "SELECT * FROM orders WHERE id = $1 AND user_id = $2",  # ownership check!
        order_id, user_id
    )
    if not order:
        raise HTTPException(404)   # 404, not 403 (don't reveal order exists)
    return order
```

### 2. Broken Authentication

```python
# INSECURE: weak password policy, no rate limiting on /login
@app.post("/auth/login")
async def login(email: str, password: str):
    user = await db.fetchrow("SELECT * FROM users WHERE email = $1", email)
    if user and user["password"] == password:  # plaintext comparison!
        return create_token(user["id"])

# SECURE:
@app.post("/auth/login")
async def login(credentials: LoginRequest, _: RateLimited):
    user = await db.fetchrow("SELECT * FROM users WHERE email = $1", credentials.email)
    # 1. Argon2 password verification (not bcrypt, not MD5, not plaintext!)
    if not user or not verify_password(credentials.password, user["hashed_password"]):
        # Same error for both cases: prevent user enumeration
        raise HTTPException(401, "Invalid credentials")
    # 2. Rate limiting on login (use Redis-backed, not in-process)
    # 3. Lock account after N failed attempts
    return {"access_token": create_token(user["id"])}
```

### 3. Broken Object Property Level Authorization (Mass Assignment)

```python
# INSECURE: accepting any field from client, including is_admin
@app.patch("/users/{user_id}")
async def update_user(user_id: int, data: dict):
    # Attacker sends {"is_admin": true} in body → gains admin!
    await db.execute("UPDATE users SET ... WHERE id = $1", **data, user_id)

# SECURE: use Pydantic schema to whitelist allowed fields
class UserUpdate(BaseModel):
    full_name: str | None = None
    email: str | None = None
    # is_admin is NOT here — can't be mass-assigned

@app.patch("/users/{user_id}")
async def update_user(user_id: int, data: UserUpdate):
    await db.execute(
        "UPDATE users SET full_name=$1, email=$2 WHERE id=$3",
        data.full_name, data.email, user_id
    )
```

### 4. Unrestricted Resource Consumption (Resource Exhaustion)

```python
# INSECURE: no limits on expensive operations
@app.get("/reports/generate")
async def generate_report(start_date: str, end_date: str):
    # Attacker requests 50 years of data → OOM / timeout
    df = await load_all_data(start_date, end_date)
    return df.to_dict()

# SECURE: validate inputs, limit result size, timeout
@app.get("/reports/generate")
async def generate_report(
    start_date: date,
    end_date: date,
    limit: int = Query(1000, le=10000),  # max 10,000 rows
    _: RateLimited,
):
    if (end_date - start_date).days > 365:  # max 1 year range
        raise HTTPException(400, "Date range too large")

    async with asyncio.timeout(30):  # kill after 30s
        df = await load_data(start_date, end_date, limit=limit)
    return df.to_dict()
```

### 5. SSRF — Server-Side Request Forgery

```python
# INSECURE: fetching user-supplied URLs from your server
@app.post("/webhooks/test")
async def test_webhook(url: str):
    # Attacker submits: url="http://169.254.169.254/latest/meta-data/iam/credentials"
    # → Your server fetches AWS metadata service → leaks AWS credentials!
    async with httpx.AsyncClient() as client:
        return await client.get(url)

# SECURE: validate URL against allowlist
import ipaddress
from urllib.parse import urlparse

ALLOWED_SCHEMES = {"https"}
BLOCKED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "169.254.169.254"}  # metadata service

def validate_webhook_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise ValueError("Only HTTPS URLs allowed")
    if parsed.hostname in BLOCKED_HOSTS:
        raise ValueError("Blocked hostname")
    # Block private IP ranges
    try:
        ip = ipaddress.ip_address(parsed.hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            raise ValueError("Private IP addresses not allowed")
    except ValueError:
        pass  # hostname is not an IP — OK
    return url
```

### 6. SQL Injection

```python
# INSECURE: string concatenation in SQL
@app.get("/users")
async def search_users(email: str):
    # Attacker: email = "' OR '1'='1" → returns all users
    # Attacker: email = "'; DROP TABLE users; --" → destroys DB!
    query = f"SELECT * FROM users WHERE email = '{email}'"
    return await db.fetch(query)

# SECURE: ALWAYS use parameterized queries
@app.get("/users")
async def search_users(email: str):
    # $1 is a parameter — never interpolated into SQL string
    return await db.fetch(
        "SELECT * FROM users WHERE email = $1",
        email  # passed separately, never embedded in SQL
    )

# asyncpg, psycopg3, SQLAlchemy: ALL support parameterized queries
# asyncpg: $1, $2, $3
# psycopg3: %s, %(name)s
# SQLAlchemy: bindparam(), text().bindparams()
# RULE: never use f-strings or .format() to build SQL queries
```

### 7. Security Misconfiguration

```python
# Common misconfigurations:
# 1. Debug mode in production (stack traces leak internals)
# 2. Default credentials (admin/admin, postgres/postgres)
# 3. Verbose error messages (expose DB schema, file paths)
# 4. Missing security headers
# 5. CORS misconfiguration (allow_origins=["*"] on internal APIs)

# FastAPI: hide details in production
app = FastAPI(
    debug=False,          # never True in production
    docs_url=None,        # disable Swagger in production
    redoc_url=None,
    openapi_url=None,
)

# Catch all errors and return generic message
@app.exception_handler(Exception)
async def generic_handler(request: Request, exc: Exception):
    # Log the full error internally
    logger.error("unhandled exception", exc_info=exc, extra={"path": request.url.path})
    # Return generic message to client (don't leak internals)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "request_id": get_request_id()}
    )

# Security headers middleware (see python-mastery capstone)
# X-Content-Type-Options: nosniff
# X-Frame-Options: DENY
# Strict-Transport-Security: max-age=31536000
# Content-Security-Policy: default-src 'self'
```

---

## Section 6 — Secrets Management

### Never Do This

```python
# BAD: hardcoded secret
DATABASE_URL = "postgresql://user:ACTUAL_PASSWORD@prod-db:5432/mydb"
JWT_SECRET = "my-super-secret"
API_KEY = "sk-1234567890abcdef"

# BAD: secret in environment variable set in Dockerfile
# ENV DATABASE_PASSWORD=mysecret  ← visible in docker history, image layers

# BAD: secret in git (even deleted commits can be found with git log --all)
```

### Environment Variables (Minimum Viable)

```python
# OK for small projects: environment variables
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str           # read from DATABASE_URL env var
    jwt_secret: str             # read from JWT_SECRET env var
    api_key: str                # read from API_KEY env var

    class Config:
        env_file = ".env"       # local dev only — .env is in .gitignore

# .env file (NEVER commit to git)
# DATABASE_URL=postgresql://user:pass@localhost/db
# JWT_SECRET=random-256-bit-hex-here

# In CI/CD: inject as environment variables from secret store
# In Kubernetes: inject from Kubernetes Secrets (encrypted at rest)
```

### HashiCorp Vault (Production Standard)

```python
# Vault: centralized secret management
# - Secrets encrypted at rest and in transit
# - Dynamic secrets: Vault generates DB credentials on demand, auto-rotates
# - Audit log: every secret access is logged
# - Leases: secrets expire automatically

import hvac

client = hvac.Client(url="https://vault.internal:8200", token=os.getenv("VAULT_TOKEN"))

# Read a static secret
secret = client.secrets.kv.v2.read_secret_version(path="myapp/database")
db_password = secret["data"]["data"]["password"]

# Dynamic database credentials (Vault creates a temporary user, auto-revokes)
db_creds = client.secrets.database.generate_credentials(name="myapp-db-role")
# Returns: {"username": "v-token-abc123", "password": "A1b2c3d4...", "lease_duration": 3600}
# Vault automatically revokes this user after 1 hour
# No shared long-lived credentials!

# AWS Secrets Manager alternative (simpler for AWS shops):
import boto3
import json

secrets = boto3.client("secretsmanager", region_name="us-east-1")
secret_string = secrets.get_secret_value(SecretId="prod/myapp/database")["SecretString"]
db_config = json.loads(secret_string)
```

### Secret Rotation Pattern

```python
# Problem: rotating a secret requires redeploying all services
# Solution: support TWO valid versions during rotation window

class DualKeyVerifier:
    """
    During key rotation, accept tokens signed with either old or new key.
    1. Deploy new key (both keys valid)
    2. Wait for old tokens to expire (or force re-login)
    3. Remove old key
    """
    def __init__(self, current_secret: str, previous_secret: str | None = None):
        self._keys = [current_secret]
        if previous_secret:
            self._keys.append(previous_secret)

    def verify(self, token: str) -> dict:
        for key in self._keys:
            try:
                return jwt.decode(token, key, algorithms=["HS256"])
            except jwt.InvalidSignatureError:
                continue
        raise ValueError("Token signature invalid with any known key")
```

---

## Section 7 — Interview Scenarios (WorldQuant-Specific)

### Scenario 1: Internal Microservices Communication

```
Question: "How would you secure service-to-service calls within your platform?"

Answer framework:
  1. mTLS for transport security (Istio service mesh or manual)
     - Each service has a certificate issued by internal CA
     - Certificate CN = service name → identity from cert, not shared secret
  
  2. Authorization at the application layer
     - Even authenticated service shouldn't have all permissions
     - Check: does "worker-service" have permission to call "settlement-service"?
  
  3. Secret management
     - No hardcoded service accounts
     - Vault with Kubernetes service account injection
  
  4. Network policies
     - Kubernetes NetworkPolicy: service A can only talk to service B, not C
```

### Scenario 2: Securing the Research Platform API

```
Question: "How would you auth researchers using your signal API?"

Answer framework:
  External researchers → OAuth 2.0 Authorization Code + PKCE
    - Researcher logs in via company SSO (SAML/OIDC)
    - Receives short-lived JWT (15 min access, 7 day refresh)
    - API key as alternative for programmatic access

  Internal services (Airflow, Spark jobs) → Client Credentials
    - Each service has client_id + client_secret in Vault
    - Tokens scoped to specific operations (read:signals, write:results)

  Rate limiting:
    - Researcher tier: 100 req/min
    - Premium researcher tier: 1000 req/min
    - Internal services: unlimited (but monitored)
```

---

## 🏋️ Exercises

### Exercise 1 — TLS Certificate Inspection
Using `openssl` or Python's `ssl` module, inspect the certificate of any HTTPS site:
- What CA signed it?
- When does it expire?
- What Subject Alternative Names does it have?

### Exercise 2 — Build a JWT Auth System
Implement a complete auth flow:
- `POST /auth/register` → hash password with argon2
- `POST /auth/login` → verify, return access + refresh tokens
- `GET /me` → verify access token
- `POST /auth/refresh` → verify refresh token, rotate, return new access
- `POST /auth/logout` → invalidate refresh token (blacklist in Redis)

### Exercise 3 — SSRF Defense
Write a Python function `validate_external_url(url: str)` that:
- Rejects non-HTTPS URLs
- Rejects private IP ranges (10.x, 172.16-31.x, 192.168.x, 127.x)
- Rejects the AWS metadata endpoint (169.254.169.254)
- Resolves the hostname to an IP and re-checks the IP (DNS rebinding defense)

---

## ✅ Self-Check Questions

1. What does TLS provide? What does it NOT provide?
2. What changed between TLS 1.2 and TLS 1.3? Why does it matter for latency?
3. What is mTLS and when would you use it?
4. What are the three parts of a JWT? What does the signature verify?
5. What is the `alg=none` JWT attack and how do you prevent it?
6. Why should refresh tokens be stored in httpOnly cookies, not localStorage?
7. What is BOLA/IDOR? Give an example and the fix.
8. What is SSRF? Why is the AWS metadata endpoint dangerous?
9. What is the difference between OAuth Authorization Code and Client Credentials flows?
10. How do you rotate a JWT secret without logging out all users simultaneously?
11. What is SQL injection and what is the one rule that prevents it?
12. Where should production secrets be stored? What is a Vault dynamic secret?

---

## 🔗 Key Links

- https://hpbn.co/transport-layer-security-tls/ — TLS deep dive (free)
- https://jwt.io/ — JWT debugger + libraries
- https://owasp.org/www-project-api-security/ — OWASP API Security Top 10
- https://developer.okta.com/blog/2019/10/21/illustrated-guide-to-oauth-and-oidc — OAuth illustrated
- https://developer.hashicorp.com/vault/docs — HashiCorp Vault docs
- https://cheatsheetseries.owasp.org/ — OWASP cheat sheets
