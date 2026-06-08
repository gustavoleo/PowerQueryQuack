"""FastAPI app factory (goal section 22).

Exposes the conversion and feedback endpoints and serves the static beta UI.
``/convert`` runs the full pipeline (analyze → convert → validate → score →
assemble) and returns the structured 10-section report.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from pqquack import __version__
from pqquack.enums import Language, OutputMode, TargetRuntime
from pqquack.feedback import ReviewRecord
from pqquack.report import convert_and_report

_WEB_DIR = Path(__file__).resolve().parents[1] / "web"


class ConvertRequest(BaseModel):
    text: str
    target_runtime: TargetRuntime = TargetRuntime.DUCKDB
    language: Language = Language.EN_US
    target_specified: bool = True


class FeedbackRequest(BaseModel):
    conversion_summary: str = ""
    sql_summary: str = ""
    verdict: str = "needs_help"  # correct | incorrect | needs_help
    language: Language = Language.EN_US
    target_runtime: TargetRuntime = TargetRuntime.DUCKDB
    notes: str | None = None


def create_app() -> FastAPI:
    app = FastAPI(
        title="Power Query Quack",
        version=__version__,
        description="From M to DuckDB, one quack at a time.",
    )

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "version": __version__}

    @app.get("/meta")
    def meta() -> dict:
        """Supported options the web UI uses to populate the settings area."""
        return {
            "languages": [lang.value for lang in Language],
            "target_runtimes": [rt.value for rt in TargetRuntime],
            "output_modes": [mode.value for mode in OutputMode],
            "defaults": {
                "language": Language.default().value,
                "target_runtime": TargetRuntime.default().value,
                "output_mode": OutputMode.default().value,
            },
        }

    @app.post("/convert")
    def convert(req: ConvertRequest) -> dict:
        if not req.text.strip():
            return {"error": "No Power Query provided."}
        report = convert_and_report(
            req.text,
            target_runtime=req.target_runtime,
            language=req.language,
            target_specified=req.target_specified,
        )
        return report.to_dict()

    @app.post("/feedback")
    def feedback(req: FeedbackRequest) -> dict:
        # Phase 7 persists these; for now we echo a well-formed review record.
        status_map = {
            "correct": "correct",
            "incorrect": "incorrect",
            "needs_help": "needs_help",
        }
        record = ReviewRecord(
            language=req.language,
            target_runtime=req.target_runtime,
            status=status_map.get(req.verdict, "needs_help"),
            original_power_query_summary=req.conversion_summary,
            generated_sql_summary=req.sql_summary,
            human_supervisor_notes=req.notes,
        )
        return {"received": True, "conversion_id": record.conversion_id}

    if _WEB_DIR.exists():
        @app.get("/")
        def index() -> FileResponse:
            return FileResponse(_WEB_DIR / "index.html")

        app.mount("/static", StaticFiles(directory=_WEB_DIR), name="static")

    return app


app = create_app()
