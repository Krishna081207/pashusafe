"""Tests for the registration profile, install visits, and live tracking.

Covers the three newer demo features end to end on a fresh in-memory DB,
with special attention to the farmer-only audience of geofence breach alerts.
"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.deps import get_db
from app.db.base import Base
from app.main import app
from app.utils.timeutil import ist_date, utcnow


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
def env(client):
    from scripts.seed import (
        DEMO_PASSWORD,
        create_farms_users,
        create_geofences,
        create_herds,
        create_install_visits,
        load_formulary,
    )

    db = next(app.dependency_overrides[get_db]())
    drugs = load_formulary(db)
    farms, users = create_farms_users(db)
    animals = create_herds(db, farms)
    create_geofences(db, farms)
    create_install_visits(db, farms, users)
    db.commit()
    mur = next(a for a in animals if a.tag_id == "MUR-002")  # any farm-1 animal

    def login(email):
        r = client.post("/api/v1/auth/login",
                        data={"username": email, "password": DEMO_PASSWORD})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    return {
        "farmer": login("ravi@demo.in"),
        "vet": login("dr.priya@demo.in"),
        "regulator": login("inspector@fssai-demo.in"),
        "admin": login("admin@demo.in"),
        "farm1": farms[0].id,
        "animal": mur,
    }


def _future_date(days_ahead: int) -> str:
    return (ist_date(utcnow()) + timedelta(days=days_ahead)).isoformat()


# ------------------------- registration ----------------------------------- #

def test_register_with_profile_and_install_request(client):
    body = {
        "full_name": "Test Patil", "email": "test.patil@example.in",
        "phone": "+91-9000000001", "password": "Secret@123",
        "farm_name": "Test Dairy", "village": "Napad", "district": "Anand",
        "state": "Gujarat", "pincode": "388001",
        "profile": {
            "species_owned": ["cattle", "buffalo"],
            "species_counts": {"cattle": 4, "buffalo": 2},
            "main_breeds": "Gir, Murrah",
        },
        "install_visit": {
            "preferred_date": _future_date(3),
            "preferred_slot": "afternoon",
            "notes": "Call before arriving.",
        },
    }
    r = client.post("/api/v1/auth/register", json=body)
    assert r.status_code == 200, r.text
    hdrs = {"Authorization": f"Bearer {r.json()['access_token']}"}

    me = client.get("/api/v1/auth/me", headers=hdrs).json()
    assert me["farm_id"] is not None

    farm = client.get(f"/api/v1/farms/{me['farm_id']}", headers=hdrs).json()
    assert farm["species_owned"] == ["cattle", "buffalo"]
    assert farm["herd_size_total"] == 6  # falls back to sum of counts
    assert farm["main_breeds"] == "Gir, Murrah"

    # the wizard's answers materialise as a starter herd (4 cattle + 2 buffalo)
    herd = client.get("/api/v1/animals", headers=hdrs).json()
    assert {a["tag_id"] for a in herd} == {"CAT-001", "CAT-002", "CAT-003", "CAT-004",
                                           "BUF-001", "BUF-002"}
    assert all(a["breed"] in ("Gir", "Murrah") for a in herd)
    assert all(a["farm_id"] == me["farm_id"] for a in herd)

    installs = client.get("/api/v1/installs", headers=hdrs).json()
    assert len(installs) == 1 and installs[0]["status"] == "requested"


def test_register_minimal_payload_still_works(client):
    r = client.post("/api/v1/auth/register", json={
        "full_name": "Legacy Farmer", "email": "legacy@example.in",
        "password": "Secret@123", "farm_name": "Legacy Farm",
    })
    assert r.status_code == 200, r.text
    # no profile given -> no starter herd invented
    hdrs = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.get("/api/v1/animals", headers=hdrs).json() == []


def test_register_rejects_past_install_date(client):
    r = client.post("/api/v1/auth/register", json={
        "full_name": "Time Traveller", "email": "tt@example.in",
        "password": "Secret@123", "farm_name": "TT Farm",
        "install_visit": {"preferred_date": _future_date(-1)},
    })
    assert r.status_code == 422


# ------------------------- install visits ---------------------------------- #

def test_install_visit_lifecycle(client, env):
    # farmer requests a slot
    r = client.post("/api/v1/installs",
                    json={"preferred_date": _future_date(2), "preferred_slot": "evening"},
                    headers=env["farmer"])
    assert r.status_code == 200, r.text
    visit_id = r.json()["id"]

    # farmer cannot self-confirm
    assert client.patch(f"/api/v1/installs/{visit_id}", json={"status": "scheduled"},
                        headers=env["farmer"]).status_code == 403

    # admin needs the full scheduling triple
    partial = {"status": "scheduled", "official_name": "Kiran Rathod"}
    assert client.patch(f"/api/v1/installs/{visit_id}", json=partial,
                        headers=env["admin"]).status_code == 422

    when = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    r = client.patch(
        f"/api/v1/installs/{visit_id}",
        json={"status": "scheduled", "scheduled_at": when,
              "official_name": "Kiran Rathod", "official_phone": "+91-9876500011"},
        headers=env["admin"],
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "scheduled"
    assert data["official_name"] == "Kiran Rathod"
    assert data["scheduled_at_display"] is not None

    # farmer-only INSTALL_UPDATE alert is visible to the farmer...
    alerts = client.get("/api/v1/alerts", headers=env["farmer"]).json()
    assert any(a["type"] == "INSTALL_UPDATE" and a["related_id"] == visit_id for a in alerts)

    # ...and hidden from every other role
    for role in ("vet", "regulator"):
        staff_alerts = client.get("/api/v1/alerts", headers=env[role]).json()
        assert not any(a["type"] == "INSTALL_UPDATE" and a["related_id"] == visit_id
                       for a in staff_alerts)

    # complete, then it is immutable
    r = client.patch(f"/api/v1/installs/{visit_id}", json={"status": "completed"},
                     headers=env["admin"])
    assert r.status_code == 200 and r.json()["completed_at_display"]
    assert client.patch(f"/api/v1/installs/{visit_id}", json={"status": "cancelled"},
                        headers=env["admin"]).status_code == 409


def test_farmer_scoped_to_own_visits(client, env):
    visits = client.get("/api/v1/installs", headers=env["farmer"]).json()
    assert visits, "seeded + created visits should exist"
    assert all(v["farm_id"] == env["farm1"] for v in visits)
    # admin sees across all farms
    admin_visits = client.get("/api/v1/installs", headers=env["admin"]).json()
    assert len(admin_visits) > len(visits)


# ------------------------- tracking / geofence ------------------------------ #

def test_non_farmers_cannot_track(client, env):
    for role in ("vet", "regulator", "admin"):
        assert client.get("/api/v1/tracking/live", headers=env[role]).status_code == 403


def test_live_tracking_returns_positions(client, env):
    r = client.get("/api/v1/tracking/live", headers=env["farmer"])
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["geofence"]["radius_m"] == 400.0  # seeded fence
    assert data["animals"], "farm 1 must have positioned animals"
    for a in data["animals"]:
        assert -90 <= a["lat"] <= 90 and -180 <= a["lng"] <= 180
        assert a["inside_geofence"] is True   # home range fits inside seeded fences


def test_geofence_put_validation_and_roundtrip(client, env):
    bad = client.put("/api/v1/tracking/geofence",
                     json={"center_lat": 22.57, "center_lng": 72.95, "radius_m": 5},
                     headers=env["farmer"])
    assert bad.status_code == 422

    payload = {"center_lat": 22.5701, "center_lng": 72.9501, "radius_m": 350}
    r = client.put("/api/v1/tracking/geofence", json=payload, headers=env["farmer"])
    assert r.status_code == 200, r.text
    got = client.get("/api/v1/tracking/geofence", headers=env["farmer"]).json()
    assert got["radius_m"] == 350 and got["enabled"] is True


def test_shrunken_fence_raises_farmer_only_breach(client, env):
    """Shrink the circle -> animals fall outside -> alert only the farmer sees."""
    r = client.put("/api/v1/tracking/geofence",
                   json={"center_lat": 22.57, "center_lng": 72.95, "radius_m": 25},
                   headers=env["farmer"])
    assert r.status_code == 200, r.text

    live = client.get("/api/v1/tracking/live", headers=env["farmer"]).json()
    assert any(a["breach"] for a in live["animals"])

    farmer_alerts = client.get("/api/v1/alerts", headers=env["farmer"]).json()
    breaches = [a for a in farmer_alerts if a["type"] == "GEOFENCE_BREACH"]
    assert breaches, "farmer must see the breach"

    for role in ("vet", "regulator", "admin"):
        staff_alerts = client.get("/api/v1/alerts", headers=env[role]).json()
        assert not any(a["type"] == "GEOFENCE_BREACH" for a in staff_alerts), role

    # staff cannot even resolve/read a farmer-only alert
    breach_id = breaches[0]["id"]
    assert client.post(f"/api/v1/alerts/{breach_id}/resolve",
                       headers=env["regulator"]).status_code == 403
    assert client.patch(f"/api/v1/alerts/{breach_id}/read",
                        headers=env["vet"]).status_code == 403

    # restoring the boundary resolves the open breach automatically
    restore = client.put("/api/v1/tracking/geofence",
                         json={"center_lat": 22.57, "center_lng": 72.95, "radius_m": 400},
                         headers=env["farmer"])
    assert restore.status_code == 200
    client.get("/api/v1/tracking/live", headers=env["farmer"])
    still_open = [a for a in client.get("/api/v1/alerts?unresolved_only=true",
                                        headers=env["farmer"]).json()
                  if a["type"] == "GEOFENCE_BREACH"]
    assert not still_open


def test_tracking_history_polyline(client, env):
    animal_id = env["animal"].id
    r = client.get(f"/api/v1/tracking/history?animal_id={animal_id}&minutes=120",
                   headers=env["farmer"])
    assert r.status_code == 200, r.text
    pts = r.json()
    assert len(pts) >= 2
    times = [p["recorded_at"] for p in pts]
    assert times == sorted(times)


def test_history_requires_own_farm(client, env):
    # find an animal from another farm via admin
    other = next(a for a in client.get("/api/v1/animals", headers=env["admin"]).json()
                 if a["farm_id"] != env["farm1"])
    r = client.get(f"/api/v1/tracking/history?animal_id={other['id']}",
                   headers=env["farmer"])
    assert r.status_code == 403
