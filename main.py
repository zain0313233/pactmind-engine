import json
import logging
import os
import time
import uuid

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from routers import process, query, analyze, compare, portfolio, agents, validate
from auth import verify_engine_auth
from rate_limit import rate_limit_middleware
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pactmind.engine")

app = FastAPI(title="PactMind AI Engine", version="1.0.0")

cors_origins = [
  origin.strip()
  for origin in os.getenv("ENGINE_CORS_ORIGINS", "").split(",")
  if origin.strip()
]

if cors_origins:
  app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
  )


@app.middleware("http")
async def engine_rate_limit_middleware(request: Request, call_next):
  return await rate_limit_middleware(request, call_next)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
  request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
  started = time.perf_counter()

  response = await call_next(request)
  response.headers["x-request-id"] = request_id

  if request.url.path != "/health":
    logger.info(
      json.dumps(
        {
          "message": "engine.request",
          "requestId": request_id,
          "method": request.method,
          "path": request.url.path,
          "status": response.status_code,
          "durationMs": round((time.perf_counter() - started) * 1000, 2),
        }
      )
    )

  return response


_engine_auth = [Depends(verify_engine_auth)]

app.include_router(process.router, prefix="/process", tags=["process"], dependencies=_engine_auth)
app.include_router(query.router, prefix="/query", tags=["query"], dependencies=_engine_auth)
app.include_router(analyze.router, prefix="/analyze", tags=["analyze"], dependencies=_engine_auth)
app.include_router(compare.router, prefix="/compare", tags=["compare"], dependencies=_engine_auth)
app.include_router(portfolio.router, prefix="/portfolio", tags=["portfolio"], dependencies=_engine_auth)
app.include_router(agents.router, prefix="/agents", tags=["agents"], dependencies=_engine_auth)
app.include_router(validate.router, prefix="/validate", tags=["validate"], dependencies=_engine_auth)


@app.get("/health")
def health():
  from db.neon import DATABASE_URL

  checks = {"api": "ok"}

  if DATABASE_URL:
    try:
      import psycopg2

      conn = psycopg2.connect(DATABASE_URL)
      cur = conn.cursor()
      cur.execute("SELECT 1")
      cur.close()
      conn.close()
      checks["database"] = "ok"
    except Exception:
      checks["database"] = "error"
  else:
    checks["database"] = "skipped"

  healthy = checks["api"] == "ok" and checks.get("database") != "error"

  return {
    "status": "healthy" if healthy else "degraded",
    "service": "pactmind-engine",
    "checks": checks,
  }
