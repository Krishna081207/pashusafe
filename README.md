# 🐄 PashuSafe — Livestock AMU & MRL Compliance Portal

**Smart India Hackathon** solution for monitoring Antimicrobial Usage (AMU) and
Maximum Residue Limit (MRL) compliance in livestock farming.

PashuSafe records animal health and every antimicrobial treatment, computes
**withdrawal periods per tissue (milk / meat / eggs)**, blocks-and-flags
**MRL violations** at sale time, and gives farmers, veterinarians, regulators
and supply-chain stakeholders live dashboards, alerts, analytics, AI risk
prediction, IoT sensor monitoring, QR traceability and a tamper-evident
blockchain-style ledger.

---

## ✨ Feature map (vs. PS deliverables)

| Deliverable | Where |
|---|---|
| Digital farm management portal | React web app, 4 roles (farmer/vet/regulator/admin), JWT auth |
| Animal health records | `/animals` — dossier per animal: treatments, sales, lab tests, sensors, ML risk |
| AMU tracking module | Treatment wizard + WHO AWaRe tagging + supervised-vs-self-treatment metric |
| MRL compliance engine | `backend/app/services/mrl_engine.py` — withdrawal clocks, overlap handling, violation rules R1–R5 |
| Automated alert system | Violation / prohibited-drug / near-miss / clearance-reminder / sensor-anomaly alerts |
| Veterinary dashboard | Prescription issuing + cross-farm visibility |
| Farmer mobile interface | Responsive Tailwind UI (works on phones; QR flow demoable on-device) |
| Analytics & reporting | AWaRe donut, monthly trend, drug leaderboard, CSV export, JSON report |
| API documentation | FastAPI Swagger at `/docs`, ReDoc at `/redoc` |

### Advanced features
- **AI/ML prediction** — MRL-violation risk (HistGradientBoosting) + disease-outbreak
  risk (LogisticRegression) trained on **synthetic demonstration data** at seed time.
  Every prediction is labeled as demo-grade in UI and API responses.
- **QR traceability** — public page per animal (`/trace/{qr}`): full medicine history,
  residue results, violations, ledger integrity badge. Scan from a phone during the demo.
- **IoT monitoring (simulated)** — deterministic collar simulator (15-min buckets):
  body temperature + activity charts, fever threshold line & anomaly alerts.
- **Blockchain-lite ledger** — append-only sha256 hash-chained events; live
  verification endpoint; admin "demo-tamper" button flips verification red on stage.
- **AI assistant** — chat about your farm data ("which animals are under withdrawal?").
  Uses **Claude with tool-use** when `ANTHROPIC_API_KEY` is set, otherwise a built-in
  offline rule-based brain over identical data tools — the demo never breaks.

## 🚀 Quickstart (local dev)

### Backend
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/seed.py          # builds demo DB + trains ML models (~30 s)
uvicorn app.main:app --reload   # http://localhost:8000/docs
```

### Frontend
```bash
cd frontend
npm install
npm run dev                     # http://localhost:5173  (proxies /api → :8000)
```

### Full stack with PostgreSQL (docker)
```bash
docker compose up --build       # postgres :5433, api :8000, web :80
```

## 🔑 Demo accounts (password `Demo@1234`)

| Role | Email |
|---|---|
| Farmer (Gujarat dairy) | `ravi@demo.in` |
| Farmer (TN poultry) | `sunita@demo.in` |
| Farmer (chronic high-use dairy) | `manoj@demo.in` |
| Veterinarian | `dr.priya@demo.in` |
| Regulator | `inspector@fssai-demo.in` |
| Admin | `admin@demo.in` |

## 🎬 Golden demo path (~4 min)

1. Login `ravi@demo.in` → dashboard tiles + open critical alerts.
2. **Record Treatment**: buffalo `MUR-001` → Enrofloxacin (*Watch* badge) → 5-day course.
3. **MRL Compliance**: MUR-001 red — milk/meat countdowns ticking.
4. **Record Sale** (milk, MUR-001): modal warns *under withdrawal* → confirm anyway.
5. Alerts bell: critical **MRL_VIOLATION** with hours-premature math.
6. Logout → `inspector@fssai-demo.in` → **Violations** shows the case →
   **Lab Tests**: record HPLC FAIL → alert upgraded to *LAB CONFIRMED*.
7. **Traceability Ledger**: verify → green; 💣 Demo-tamper → verify → red at block N.
8. Open `/trace/{qr}` logged-out (or scan QR from an animal's page on a phone):
   public medicine/residue/violation history + tamper badge.
9. Ask the assistant: *"Which animals are under withdrawal?"*, *"Any MRL violations this month?"*
10. **Analytics**: AWaRe donut, trends; dashboard watchlist ranks the chronic farm highest.

## 🧠 How the MRL engine works

```
last dose day ──► N full calendar days (IST, N = ceil(labelled WP)) ──► clears 23:59:59 IST
```
- One clock **per tissue** the animal currently produces (lactating ⇒ milk;
  laying hens ⇒ eggs; everyone ⇒ meat). Fractional WPs round **up** (safe side).
- Overlapping/stacked drugs collapse to the **longest** clock per tissue.
- Sale inside any active window ⇒ frozen-evidence violation (`sale_events.is_violation`)
  + critical alert + ledger entry. Within 24 h *after* clearance ⇒ near-miss info alert.
- Lab FAIL confirms a violation; lab PASS inside a theoretical window clears it early
  with evidence. Banned drugs (colistin) trigger immediate regulatory alerts.

## ⚗️ What is real vs simulated

| Component | Status |
|---|---|
| Withdrawal math, violation detection, alerts, ledger chain, RBAC | Real deterministic logic (+ pytest coverage) |
| Drug formulary WP/MRL values | Approximate Codex/FSSAI figures for demo purposes |
| Farm/animal/treatment/sale history | Seeded synthetic Indian-context dataset |
| ML models & IoT sensor feed | Trained/simulated on synthetic data — clearly labeled in UI/API |
| AI assistant | Live Claude tool-use when API key present; offline fallback otherwise |

## 🔧 Configuration (env vars)

| Var | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./pashusafe.db` | SQLite or `postgresql+psycopg://...` |
| `JWT_SECRET` | dev default | Set in production |
| `ENVIRONMENT` | `development` | gates `/ledger/demo-tamper` |
| `ANTHROPIC_API_KEY` | unset | enables Claude assistant mode |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-5` | model override |

## ✅ Tests

```bash
cd backend && pytest -q
```
Covers: tissue applicability, calendar-day clearance math, fractional-WP rounding,
overlap collapse, sale verdicts (violation/near-miss/clean), hash-chain build +
tamper detection, plus API smoke tests incl. cross-tenant access control.

## 📁 Repository layout

```
backend/app/services/mrl_engine.py    ← core compliance engine
backend/scripts/seed.py               ← deterministic demo dataset + ML training
frontend/src/pages/                   ← role-scoped screens
docs: FastAPI /docs (OpenAPI)         ← auto-generated API documentation
```
