# Milestone 1 — TDD Walkthrough

This guide explains **what we built**, **why**, and **how each piece connects** — using diagrams and the actual code.

## TDD Approach We Used

We did **vertical slices**, not "write all tests then all code":

```
Slice 1: test health  → implement /health           ✅
Slice 2: test register → implement user + register  ✅
Slice 3: test login   → implement JWT login       ✅
Slice 4: test /me     → implement auth guard      ✅
```

Each slice goes: **RED** (failing test) → **GREEN** (minimal code) → move on.

---

## The Big Picture (Milestone 1)

```
┌─────────────┐         HTTP          ┌─────────────┐         SQL         ┌─────────────┐
│   Browser   │ ────────────────────▶ │  FastAPI    │ ──────────────────▶ │ PostgreSQL  │
│  (Next.js)  │ ◀──────────────────── │  (API)      │ ◀────────────────── │  (users)    │
└─────────────┘    JSON + JWT token    └─────────────┘                     └─────────────┘
       │                                      │
       │  /login  /register  /dashboard       │  /health
       └──────────────────────────────────────┘  /v1/auth/*
```

**What a user can do today:**
1. Register with email + password
2. Log in and get a JWT
3. See an empty dashboard (protected route)

---

## Slice 1: Health Check — "Is the API alive?"

### Picture

```
Test (httpx)  ──GET /health──▶  FastAPI  ──returns──▶  {"status": "ok"}
```

### Test (RED first)

```python
# tests/test_health.py
async def test_health_returns_ok():
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "xautopilot-api"}
```

### Code (GREEN)

```python
# src/xautopilot/main.py
@app.get("/health")
async def health():
    return {"status": "ok", "service": "xautopilot-api"}
```

**Why it matters:** Every service needs a health endpoint for Docker, load balancers, and monitoring.

---

## Slice 2: Registration — "Create a creator account"

### Picture

```
POST /v1/auth/register
        │
        ▼
┌───────────────┐    hash password    ┌───────────────┐
│  auth router  │ ──────────────────▶ │  users table  │
└───────────────┘    (bcrypt)         └───────────────┘
        │
        ▼
   201 { id, email }   (no password in response!)
```

### Test

```python
async def test_register_creates_user(client):
    response = await client.post("/v1/auth/register", json={
        "email": "creator@example.com",
        "password": "securepass123",
    })
    assert response.status_code == 201
    assert "password" not in response.json()
```

### Key files

| File | Role |
|------|------|
| `models/user.py` | Database table definition |
| `services/auth_service.py` | Business logic (hash, save) |
| `routers/auth.py` | HTTP endpoint |
| `schemas/auth.py` | Request/response shapes |

**Layer pattern:**

```
HTTP Request → Router → Service → Model → Database
                ↑          ↑
            validates   business rules
            with Pydantic
```

---

## Slice 3: Login — "Prove who you are, get a token"

### Picture

```
POST /v1/auth/login { email, password }
        │
        ▼
   verify bcrypt hash
        │
        ▼
   create JWT ──▶ { access_token: "eyJ..." }
```

JWT = a signed note that says "this is user X, valid for 15 min".

### Test

```python
async def test_login_returns_access_token(client):
    await client.post("/v1/auth/register", json={...})
    response = await client.post("/v1/auth/login", json={...})
    assert "access_token" in response.json()
```

### Code flow

```python
# token_service.py — signs the token
jwt.encode({"sub": str(user_id), "exp": expire}, SECRET_KEY)

# auth_service.py — checks password
bcrypt.checkpw(password.encode(), user.password_hash.encode())
```

---

## Slice 4: Protected Route — "Only logged-in users"

### Picture

```
GET /v1/auth/me
Header: Authorization: Bearer eyJ...
        │
        ▼
┌─────────────────┐
│ get_current_user │ ── decode JWT ──▶ find user in DB
└─────────────────┘
        │
        ▼
   200 { id, email }     or     401 Unauthorized
```

### Test

```python
async def test_me_returns_current_user(client):
    token = await _register_and_login(client)
    response = await client.get("/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"})
    assert response.json()["email"] == "creator@example.com"
```

### Dependency injection (FastAPI magic)

```python
# dependencies.py
async def get_current_user(credentials = Depends(security), db = Depends(get_db)):
    user_id = decode_access_token(credentials.credentials)
    return await get_user_by_id(db, user_id)

# routers/auth.py
@router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    return current_user
```

Any route that adds `Depends(get_current_user)` is automatically protected.

---

## Frontend: How the Web App Connects

### Picture

```
/login ──▶ api.login() ──▶ POST /v1/auth/login ──▶ save token in localStorage
                                                              │
/dashboard ──▶ api.me(token) ──▶ GET /v1/auth/me ─────────────┘
```

### API client (`apps/web/src/lib/api-client.ts`)

Thin wrapper over `fetch` — one function per endpoint.

### Auth storage (`apps/web/src/lib/auth.ts`)

Token lives in `localStorage` for MVP. (Post-MVP: httpOnly cookies.)

---

## Project Structure (What Goes Where)

```
apps/
├── api/                    ← Backend (FastAPI)
│   ├── src/xautopilot/
│   │   ├── main.py         ← App entry, routes mounted here
│   │   ├── routers/        ← HTTP endpoints (thin)
│   │   ├── services/       ← Business logic (thick)
│   │   ├── models/         ← Database tables
│   │   └── schemas/        ← API contracts (Pydantic)
│   └── tests/              ← Integration tests (public API only)
│
└── web/                    ← Frontend (Next.js)
    └── src/
        ├── app/            ← Pages (login, register, dashboard)
        └── lib/            ← API client, auth helpers
```

---

## Running Locally

```bash
# Terminal 1 — infrastructure
cd ~/Projects/x-autopilot
docker compose up postgres redis -d

# Terminal 2 — API
cd apps/api
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn xautopilot.main:app --reload

# Terminal 3 — Web
cd apps/web
npm run dev

# Terminal 4 — Tests (TDD loop)
cd apps/api && pytest tests/ -v
```

Open http://localhost:3000 → Register → Dashboard.

---

## What's Next (Milestone 2)

```
Voice Profile ──▶ Knowledge Sources ──▶ Ingestion ──▶ RAG
```

We'll TDD each of those the same way: one behavior, one test, one implementation.
