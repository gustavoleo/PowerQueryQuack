"""FastAPI app factory.

Phase 0 exposes health and metadata endpoints so the service is runnable and
testable end-to-end before the ``/convert`` and ``/feedback`` endpoints land in
Phases 6-7. Keeping a factory (``create_app``) makes testing and configuration
straightforward.
"""

from __future__ import annotations

from fastapi import FastAPI

from pqquack import __version__
from pqquack.enums import Language, OutputMode, TargetRuntime


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

    return app


app = create_app()
