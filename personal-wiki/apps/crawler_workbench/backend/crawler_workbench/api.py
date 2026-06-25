from __future__ import annotations

from fastapi import APIRouter, Request


router = APIRouter(prefix="/api")


@router.get("/health")
def health(request: Request) -> dict[str, object]:
    settings = request.app.state.settings
    return {
        "status": "ok",
        "bind_host": settings.bind_host,
        "bind_port": settings.bind_port,
        "authenticated": False,
        "warning": settings.trusted_network_warning,
    }
