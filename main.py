import os
import time
import uuid
from collections import defaultdict

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# =====================================================
# Configuration
# =====================================================

EMAIL = "23f1000212@ds.study.iitm.ac.in"

ALLOWED_ORIGIN = os.getenv(
    "Q10_ALLOWED_ORIGIN",
    "https://app-ah3n9p.example.com"
)

RATE_LIMIT = int(
    os.getenv("Q10_RATE_LIMIT", "12")
)

WINDOW = 10  # seconds

client_hits = defaultdict(list)

# =====================================================
# CORS Middleware
# =====================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        ALLOWED_ORIGIN,
        "https://exam.sanand.workers.dev",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "X-Request-ID",
        "Retry-After",
    ],
)

# =====================================================
# Request Context Middleware
# =====================================================

@app.middleware("http")
async def request_context(request: Request, call_next):

    request_id = request.headers.get("X-Request-ID")

    if not request_id:
        request_id = str(uuid.uuid4())

    request.state.request_id = request_id

    response = await call_next(request)

    response.headers["X-Request-ID"] = request_id

    return response


# =====================================================
# Rate Limiting Middleware
# =====================================================

@app.middleware("http")
async def rate_limit(request: Request, call_next):

    # Skip OPTIONS requests (CORS preflight)
    if request.method == "OPTIONS":
        return await call_next(request)

    client_id = request.headers.get("X-Client-Id", "anonymous")

    now = time.time()

    hits = [
        t
        for t in client_hits[client_id]
        if now - t < WINDOW
    ]

    client_hits[client_id] = hits

    if len(hits) >= RATE_LIMIT:

        retry_after = max(
            1,
            int(WINDOW - (now - hits[0])) + 1
        )

        response = JSONResponse(
            status_code=429,
            content={
                "detail": "Too Many Requests"
            }
        )

        response.headers["Retry-After"] = str(retry_after)

        response.headers["X-Request-ID"] = getattr(
            request.state,
            "request_id",
            str(uuid.uuid4())
        )

        return response

    hits.append(now)
    client_hits[client_id] = hits

    return await call_next(request)


# =====================================================
# Ping Endpoint
# =====================================================

@app.get("/ping")
async def ping(request: Request):

    return {
        "email": EMAIL,
        "request_id": request.state.request_id
    }
