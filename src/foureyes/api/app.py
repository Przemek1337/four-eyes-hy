from __future__ import annotations

from fastapi import FastAPI, Query
from fastapi.responses import PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from pathlib import Path

from foureyes.core.context import Services
from foureyes.engine import Engine

from . import admin, chat, mcp

UI_DIST = Path(__file__).resolve().parent.parent / "ui_dist"


def create_app(services: Services) -> FastAPI:
    app = FastAPI(title="FourEyes Gateway", version="0.1.0")
    app.state.services = services
    app.state.engine = Engine(services)
    app.include_router(chat.router)
    app.include_router(mcp.router)
    app.include_router(admin.router)

    @app.get("/healthz")
    def healthz():
        return {"status": "ok", "policy_version": services.policy_store.current().label}

    @app.get("/audit/export")
    def audit_export(format: str = Query("jsonl", pattern="^(jsonl|csv)$"), decision: str | None = None,
                     agent: str | None = None, session: str | None = None, rule: str | None = None,
                     owasp: str | None = None, data_class: str | None = None,
                     from_: str | None = Query(None, alias="from"), to: str | None = None,
                     events: str | None = Query(None, pattern="^(decisions|policy|usage)(,(decisions|policy|usage))*$")):
        text = services.audit.export(format, decision=decision, agent=agent, session=session, rule=rule,
                                     owasp=owasp, data_class=data_class, from_ts=from_, to_ts=to,
                                     events=events.split(",") if events else None)
        media = "text/csv" if format == "csv" else "application/x-ndjson"
        return PlainTextResponse(text, media_type=media,
                                 headers={"Content-Disposition": f"attachment; filename=audit.{format}"})

    if UI_DIST.is_dir():
        app.mount("/ui", StaticFiles(directory=UI_DIST, html=True), name="ui")

    @app.get("/", include_in_schema=False)
    def root():
        return RedirectResponse("/ui/" if UI_DIST.is_dir() else "/docs")

    return app
