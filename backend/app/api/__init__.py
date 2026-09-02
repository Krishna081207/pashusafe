from fastapi import APIRouter
from app.api.v1.endpoints.mrl import router as mrl_router

api_router = APIRouter()
api_router.include_router(mrl_router, prefix="/mrl", tags=["MRL & AMU Compliance"])