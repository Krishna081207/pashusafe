from fastapi import APIRouter

from app.api.v1.routers import (
    administrations,
    alerts,
    analytics,
    animals,
    assistant,
    auth,
    drugs,
    farms,
    installs,
    iot,
    ledger,
    ml,
    mrl,
    prescriptions,
    residue_tests,
    sales,
    trace,
    tracking,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(farms.router)
api_router.include_router(animals.router)
api_router.include_router(drugs.router)
api_router.include_router(prescriptions.router)
api_router.include_router(administrations.router)
api_router.include_router(mrl.router)
api_router.include_router(sales.router)
api_router.include_router(residue_tests.router)
api_router.include_router(alerts.router)
api_router.include_router(analytics.router)
api_router.include_router(iot.router)
api_router.include_router(installs.router)
api_router.include_router(tracking.router)
api_router.include_router(trace.router)
api_router.include_router(ledger.router)
api_router.include_router(assistant.router)
api_router.include_router(ml.router)
