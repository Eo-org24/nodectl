from __future__ import annotations

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse


router = APIRouter()


@router.get("/healthz")
async def healthz(request: Request) -> JSONResponse:
    if getattr(request.app.state, "health_ready", False):
        return JSONResponse({"status": "ok"}, status_code=status.HTTP_200_OK)
    detail = getattr(request.app.state, "health_error", "") or "starting"
    return JSONResponse({"status": "error", "detail": detail}, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
