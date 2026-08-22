#!/usr/bin/env python3
"""Hit every endpoint the UI uses (against the real DB) and print which ones
fail, with full tracebacks.

    ./.venv/bin/python scripts/debug_http.py
"""

import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

ENDPOINTS = [
    "GET /api/v1/auth/me",
    "GET /api/v1/farms",
    "GET /api/v1/farms/1",
    "GET /api/v1/animals",
    "GET /api/v1/animals/1",
    "GET /api/v1/drugs",
    "GET /api/v1/mrl/status/farm/1",
    "GET /api/v1/mrl/status/animal/1",
    "GET /api/v1/mrl/status/overview",
    "GET /api/v1/mrl/violations",
    "GET /api/v1/alerts",
    "GET /api/v1/sale-events",
    "GET /api/v1/residue-tests",
    "GET /api/v1/prescriptions",
    "GET /api/v1/administrations",
    "GET /api/v1/analytics/dashboard",
    "GET /api/v1/analytics/amu",
    "GET /api/v1/analytics/sales",
    "GET /api/v1/analytics/compliance/by-farm",
    "GET /api/v1/iot/readings?animal_id=1&hours=24",
    "GET /api/v1/iot/latest",
    "GET /api/v1/ml/predict/animal/1",
    "GET /api/v1/ml/predict/farm/1",
    "GET /api/v1/ml/model/info",
    "GET /api/v1/ledger/events",
    "GET /api/v1/ledger/verify",
    "GET /api/v1/assistant/suggestions",
    "GET /trace/whatever-public-404-expected",
]


def main():
    # raise_server_exceptions=True -> the real traceback surfaces HERE instead
    # of being swallowed into a plain-text 500 response.
    with TestClient(app, raise_server_exceptions=True) as client:
        r = client.post(
            "/api/v1/auth/login",
            data={"username": "ravi@demo.in", "password": "Demo@1234"},
        )
        if r.status_code != 200:
            print("LOGIN FAILED:", r.status_code, r.text[:200])
            return
        hdr = {"Authorization": f"Bearer {r.json()['access_token']}"}
        print("login OK\n")

        failures = 0
        for spec in ENDPOINTS:
            method, path = spec.split(" ", 1)
            try:
                r = client.request(method, path, headers=hdr)
            except Exception:
                print(f"[ERR ] {method} {path}")
                traceback.print_exc()
                failures += 1
                continue
            if r.status_code >= 500:
                failures += 1
                print(f"[{r.status_code}] {method} {path}")
                body = r.text[:300]
                print(f"       body: {body}")
            else:
                print(f"[{r.status_code}] {method} {path}")

        print(f"\n{'!' * 20} {failures} endpoint(s) failing with 5xx")
        print("If any 500s above: re-run with raise_server_exceptions to see traceback:")
        print("  (the uvicorn terminal also prints the full traceback on each 500)")


if __name__ == "__main__":
    main()
