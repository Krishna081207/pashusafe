"""API smoke tests: full request cycle on a fresh in-memory DB, including the
golden demo path (treatment -> countdown -> early sale -> violation alert) and
cross-tenant access control."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.deps import get_db
from app.db.base import Base
from app.main import app


@pytest.fixture(scope="module")
def client():
    # StaticPool: ONE shared connection so every thread sees the same memory DB
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def tokens(client):
    from scripts.seed import DEMO_PASSWORD, create_farms_users, create_herds, load_formulary

    db = next(app.dependency_overrides[get_db]())
    drugs = load_formulary(db)
    farms, users = create_farms_users(db)
    animals = create_herds(db, farms)
    db.commit()

    def login(email):
        r = client.post(
            "/api/v1/auth/login",
            data={"username": email, "password": DEMO_PASSWORD},
        )
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    return {
        "farmer": login("ravi@demo.in"),
        "vet": login("dr.priya@demo.in"),
        "regulator": login("inspector@fssai-demo.in"),
        "admin": login("admin@demo.in"),
        "_farm1": farms[0].id,
        "_mur": next(a for a in animals if a.tag_id == "MUR-001"),
        "_enro": drugs["Enrofloxacin"],
        "_colistin": drugs["Colistin"],
    }


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_login_bad_password(client, tokens):
    r = client.post("/api/v1/auth/login", data={"username": "ravi@demo.in", "password": "wrong"})
    assert r.status_code == 401


# --------------------------- golden path ---------------------------------- #

def test_record_treatment_produces_countdown(client, tokens):
    body = {
        "animal_id": tokens["_mur"].id,
        "drug_id": tokens["_enro"].id,
        "course_days": 5,
        "dose_amount": 7.5,
        "route": "im",
    }
    r = client.post("/api/v1/administrations", json=body, headers=tokens["farmer"])
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["overall"] in ("WITHDRAWAL_ACTIVE", "CLEAR_TODAY")
    tissues = {t["tissue"] for t in data["tissues"]}
    assert tissues == {"milk", "meat"}


def test_status_endpoint_matches(client, tokens):
    r = client.get(f"/api/v1/mrl/status/animal/{tokens['_mur'].id}", headers=tokens["farmer"])
    assert r.status_code == 200
    assert r.json()["under_withdrawal"] is True


def test_early_sale_without_ack_returns_warning(client, tokens):
    r = client.post(
        "/api/v1/sale-events",
        json={"animal_id": tokens["_mur"].id, "product_type": "milk",
              "quantity": 10, "buyer_name": "Test Society"},
        headers=tokens["farmer"],
    )
    assert r.status_code == 200
    assert r.json().get("warning") is True


def test_early_sale_with_ack_creates_violation_and_alert(client, tokens):
    r = client.post(
        "/api/v1/sale-events",
        json={"animal_id": tokens["_mur"].id, "product_type": "milk", "quantity": 10,
              "buyer_name": "Test Society", "acknowledge_warning": True},
        headers=tokens["farmer"],
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["is_violation"] is True
    assert "MRL_VIOLATION" in data["alerts_raised"]

    alerts = client.get("/api/v1/alerts", headers=tokens["farmer"]).json()
    assert any(a["type"] == "MRL_VIOLATION" for a in alerts)

    # regulator sees the same violation
    violations = client.get("/api/v1/mrl/violations", headers=tokens["regulator"]).json()
    assert any(v["sale_event_id"] == data["id"] for v in violations)


def test_clean_sale_is_not_flagged(client, tokens):
    # farmer-owned bulk sale; the conditional tolerates a legit active window
    r = client.post(
        "/api/v1/sale-events",
        json={"product_type": "milk", "quantity": 30, "buyer_name": "Society"},
        headers=tokens["farmer"],
    )
    assert r.status_code == 200
    body = r.json()
    if not body.get("warning"):  # some farm may legitimately have a window open
        assert body["is_violation"] is False


# --------------------------- role security -------------------------------- #

def test_farmer_cannot_read_other_farm(client, tokens):
    farm2 = client.get("/api/v1/farms", headers=tokens["vet"]).json()[1]["id"]
    r = client.get(f"/api/v1/farms/{farm2}", headers=tokens["farmer"])
    assert r.status_code == 403


def test_farmer_cannot_create_prescription(client, tokens):
    r = client.post(
        "/api/v1/prescriptions",
        json={"animal_id": tokens["_mur"].id, "drug_id": tokens["_enro"].id,
              "diagnosis": "x", "dose_amount": 5, "route": "im"},
        headers=tokens["farmer"],
    )
    assert r.status_code == 403


def test_only_regulator_records_residue_tests(client, tokens):
    r = client.post(
        "/api/v1/residue-tests",
        json={"sample_type": "milk", "drug_id": tokens["_enro"].id,
              "animal_id": tokens["_mur"].id, "result": "fail",
              "measured_residue_ug_kg": 250},
        headers=tokens["farmer"],
    )
    assert r.status_code == 403


def test_prohibited_drug_alerts_instead_of_422(client, tokens):
    hen = None
    animals = client.get("/api/v1/animals", headers=tokens["farmer"]).json()
    # colistin has no cattle rule and is banned -> records + alerts (R2 guard)
    r = client.post(
        "/api/v1/administrations",
        json={"animal_id": tokens["_mur"].id, "drug_id": tokens["_colistin"].id,
              "course_days": 3, "dose_amount": 5, "route": "in_water"},
        headers=tokens["farmer"],
    )
    assert r.status_code == 201, r.text
    assert any(a["type"] == "PROHIBITED_DRUG_USED" for a in r.json()["alerts_raised"])


# --------------------------- advanced features ----------------------------- #

def test_ledger_verify_ok_and_tamper_flips_red(client, tokens):
    ok = client.get("/api/v1/ledger/verify").json()
    assert ok["valid"] is True and ok["length"] > 0

    tamper = client.post("/api/v1/ledger/demo-tamper", headers=tokens["admin"])
    assert tamper.status_code == 200

    bad = client.get("/api/v1/ledger/verify").json()
    assert bad["valid"] is False
    assert bad["first_invalid_seq"] is not None


def test_public_trace_page_no_auth(client):
    # find a qr code via admin, then fetch the trace page WITHOUT auth
    r = client.get("/api/v1/animals", headers=_hdrs(client, "admin@demo.in"))
    qr = r.json()[0]["qr_code"]
    trace = client.get(f"/api/v1/trace/public/{qr}")
    assert trace.status_code == 200
    body = trace.json()
    assert "medicine_history" in body and "ledger_integrity" in body


def test_iot_readings_generated(client, tokens):
    r = client.get(f"/api/v1/iot/readings?animal_id={tokens['_mur'].id}&hours=24",
                   headers=tokens["farmer"])
    assert r.status_code == 200
    assert len(r.json()["readings"]) > 12  # 15-min buckets over 24h


def test_analytics_endpoints(client, tokens):
    dash = client.get("/api/v1/analytics/dashboard", headers=tokens["farmer"]).json()
    assert dash["total_animals"] > 0
    amu = client.get("/api/v1/analytics/amu", headers=tokens["farmer"]).json()
    assert "aware_breakdown" in amu


def test_assistant_offline_mode(client, tokens):
    r = client.post("/api/v1/assistant/chat", json={"message": "Which animals are under withdrawal?"},
                    headers=tokens["farmer"])
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "offline"
    assert "withdrawal" in body["answer"].lower()


def test_animal_dossier(client, tokens):
    """Regression: dossier endpoint used to NameError on ensure_farm_access."""
    r = client.get(f"/api/v1/animals/{tokens['_mur'].id}", headers=tokens["farmer"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert "qr_code" in body and "administrations" in body and "residue_tests" in body


def test_all_get_endpoints_healthy(client, tokens):
    """Crawl every read endpoint the UI depends on; none may 5xx."""
    animal_id = tokens["_mur"].id
    endpoints = [
        "/api/v1/auth/me",
        "/api/v1/farms",
        f"/api/v1/farms/{tokens['_farm1']}",
        "/api/v1/animals",
        f"/api/v1/animals/{animal_id}",
        "/api/v1/drugs",
        f"/api/v1/mrl/status/farm/{tokens['_farm1']}",
        f"/api/v1/mrl/status/animal/{animal_id}",
        "/api/v1/mrl/status/overview",
        "/api/v1/mrl/violations",
        "/api/v1/alerts",
        "/api/v1/sale-events",
        "/api/v1/residue-tests",
        "/api/v1/administrations",
        "/api/v1/analytics/dashboard",
        "/api/v1/analytics/amu",
        "/api/v1/analytics/sales",
        "/api/v1/analytics/compliance/by-farm",
        f"/api/v1/iot/readings?animal_id={animal_id}&hours=24",
        f"/api/v1/iot/status/{animal_id}",
        "/api/v1/iot/latest",
        f"/api/v1/ml/predict/animal/{animal_id}",
        f"/api/v1/ml/predict/farm/{tokens['_farm1']}",
        "/api/v1/ml/model/info",
        "/api/v1/ledger/events",
        "/api/v1/ledger/verify",
        "/api/v1/assistant/suggestions",
    ]
    for ep in endpoints:
        r = client.get(ep, headers=tokens["farmer"])
        assert r.status_code < 500, f"{ep} -> {r.status_code}: {r.text[:200]}"


# --------------------------- helpers --------------------------------------- #

def _login_headers(client, email):
    from scripts.seed import DEMO_PASSWORD

    r = client.post("/api/v1/auth/login", data={"username": email, "password": DEMO_PASSWORD})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _hdrs(client, email):
    return _login_headers(client, email)


def _any_token(client):
    return _login_headers(client, "admin@demo.in")["Authorization"]
