from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .db import check_database
from .routes import router

app = FastAPI(title="MusicScope API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"], allow_methods=["*"], allow_headers=["*"])
app.include_router(router)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "api"}


@app.get("/health/db", tags=["system"])
def database_health() -> JSONResponse:
    try:
        check_database()
    except Exception:
        return JSONResponse(status_code=503, content={"status": "unavailable", "service": "database"})
    return JSONResponse(content={"status": "ok", "service": "database"})
