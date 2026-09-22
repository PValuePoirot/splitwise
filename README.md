# Splitwise

A full end-to-end expense-splitting app. Users authenticate, create groups, add members, record expenses with **multiple payers and multiple debtors** split by equal / exact / percentage, view running balances, and record settlements to settle up.

## Stack

| Layer      | Technology                                   |
| ---------- | -------------------------------------------- |
| Backend    | FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2 |
| Frontend   | React 18, Vite, TypeScript, Tailwind CSS    |
| Database   | Postgres (Neon free tier)                    |
| Auth       | JWT (access + rotating refresh), Argon2     |
| Hosting    | Render (web service + static site)          |

## Features

- **Account auth** — register, login, refresh, logout. Passwords hashed with Argon2; JWT access (30m) + refresh (30d) tokens.
- **Groups** — create groups, invite members by email, remove members.
- **Expenses** — multiple payers AND multiple debtors per expense. Split by equal, exact amounts, or percentages. Server validates that paid shares and owed shares each sum to the total.
- **Balances** — running per-user net balance per group. Positive = owed money, negative = owes.
- **Debt simplification** — greedy min-transactions algorithm suggests the fewest payments to settle a group.
- **Settlements** — record payments between members; balances update accordingly.
- **Security** — per-route authorization (only group members access their group), Pydantic validation, parameterized queries, CORS allowlist, rate limiting on auth endpoints, `Decimal` for money (no float rounding), `password_hash` never serialized.

## Project structure

```
splitwise/
├── backend/          # FastAPI app
│   ├── app/
│   │   ├── main.py           # FastAPI app + middleware
│   │   ├── config.py         # env-driven settings
│   │   ├── database.py       # SQLAlchemy engine + session
│   │   ├── models/           # ORM models
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── routers/          # auth, groups, expenses, settlements
│   │   ├── services/         # balances + debt simplification
│   │   ├── auth/             # hashing, JWT, dependencies
│   │   └── core/             # exceptions, rate limiter
│   ├── alembic/              # DB migrations
│   ├── tests/                # pytest suite (37 tests)
│   └── requirements.txt
├── frontend/         # Vite + React + TS
│   ├── src/
│   │   ├── api/              # typed API client with refresh
│   │   ├── components/       # UI primitives
│   │   ├── context/          # AuthContext
│   │   ├── pages/            # Auth, Groups, GroupDetail
│   │   └── types/            # TS types mirroring backend
│   └── package.json
├── render.yaml       # Render deployment blueprint
└── .env.example      # env var template (no secrets)
```

## Local development

### Prerequisites
- Python 3.11+
- Node 18+
- A Postgres database (local or Neon)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Create backend/.env (see ../.env.example)
cp ../.env.example .env
# Edit .env: set DATABASE_URL, JWT_SECRET, JWT_REFRESH_SECRET

# Run migrations
alembic upgrade head

# Start the API
uvicorn app.main:app --reload --port 8000
# Docs at http://localhost:8000/docs
```

### Frontend

```bash
cd frontend
npm install
# Create frontend/.env with VITE_API_URL=http://localhost:8000
npm run dev
# App at http://localhost:5173
```

### Tests

```bash
cd backend
source .venv/bin/activate
python -m pytest
```

## Deployment (Render + Neon)

### 1. Create a Neon Postgres database
1. Sign up at [neon.tech](https://neon.tech) (free tier: 0.5GB).
2. Create a project, copy the **pooled** connection string.
3. It looks like: `postgresql+psycopg2://user:pass@ep-xxx.region.aws.neon.tech/dbname?sslmode=require`

### 2. Deploy via Render Blueprint
1. Push this repo to GitHub.
2. Go to [Render → New → Blueprint](https://dashboard.render.com/blueprints).
3. Select this repository. Render reads `render.yaml` and creates two services:
   - `splitwise-api` (web service, FastAPI)
   - `splitwise-web` (static site, React)
4. In the Render dashboard, set the env vars marked `sync: false`:
   - `DATABASE_URL` → your Neon connection string (on the API service)
   - `FRONTEND_URL` → the static site URL (e.g. `https://splitwise-web.onrender.com`) on the API service
   - `VITE_API_URL` → the API URL (e.g. `https://splitwise-api.onrender.com`) on the web service
5. Render auto-generates `JWT_SECRET` and `JWT_REFRESH_SECRET`.
6. Deploy. The API health check is at `/health`.

### 3. Run migrations on the production DB
After the first deploy, run migrations against Neon:
```bash
cd backend
DATABASE_URL="your-neon-url" alembic upgrade head
```

## API overview

| Method | Path                                  | Description              |
| ------ | ------------------------------------- | ------------------------ |
| POST   | `/auth/register`                      | Create account           |
| POST   | `/auth/login`                         | Get tokens               |
| POST   | `/auth/refresh`                       | Refresh access token     |
| GET    | `/auth/me`                            | Current user             |
| GET    | `/groups`                             | List my groups           |
| POST   | `/groups`                             | Create group             |
| GET    | `/groups/{id}`                        | Group detail + members   |
| POST   | `/groups/{id}/members`               | Add member by email      |
| DELETE | `/groups/{id}/members/{user_id}`     | Remove member            |
| GET    | `/groups/{id}/balances`              | Balances + simplified debts |
| GET    | `/groups/{id}/expenses`              | List expenses            |
| POST   | `/groups/{id}/expenses`              | Create expense           |
| DELETE | `/groups/{id}/expenses/{expense_id}`  | Delete expense           |
| GET    | `/groups/{id}/settlements`            | List settlements         |
| POST   | `/groups/{id}/settlements`            | Record settlement        |

## Security notes

- Passwords hashed with Argon2 (2015 Password Hashing Competition winner).
- JWT access tokens (30 min) + refresh tokens (30 days, rotating).
- All request bodies validated with Pydantic v2.
- Per-route authorization: only group members can read/mutate their group's data.
- Money stored as `Numeric(12,2)` in Postgres and `Decimal` in Python — no float rounding errors.
- CORS allowlist (not `*`), rate limiting on auth endpoints, `password_hash` never serialized.
- All secrets via environment variables; `.env` is gitignored.
