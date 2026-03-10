from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import pathlib

# Patch to add Web UI routes to existing main.py
# Add these lines to app/main.py after app is created:
#
#   from app.ui import mount_ui
#   mount_ui(app)

def mount_ui(app):
    """Mount the Web UI on the FastAPI app."""
    static_dir = pathlib.Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/inbox", include_in_schema=False)
    @app.get("/compose", include_in_schema=False)
    @app.get("/", include_in_schema=False)
    async def serve_ui():
        return FileResponse(str(static_dir / "index.html"))
