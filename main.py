import time
import uuid
from collections import defaultdict

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

EMAIL = "23f1000212@ds.study.iitm.ac.in"

RATE_LIMIT = 12
WINDOW = 10

client_hits = defaultdict(list)

# ----------------------------
# CORS
# ----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://app-ah3n9p.example.com",
        "https://exam.sanand.workers.dev",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "Retry-After"],
)

# ----------------------------
# Request Context Middleware
# ----------------------------
@app.middleware("http")
async def request_context(request: Request, call_next):

    request_id = request.headers.get("X-Request-ID")

    if not request_id:
        request_id = str(uuid.uuid4())

    request.state.request_id = request_id

    response = await call_next(request)

    response.headers["X-Request-ID"] = request_id

    return response


# ----------------------------
# Rate Limit Middleware
# ----------------------------
@app.middleware("http")
async def rate_limit(request: Request, call_next):

    # Skip CORS preflight
    if request.method == "OPTIONS":
        return await call_next(request)

    client = request.headers.get("X-Client-Id", "default")

    now = time.time()

    hits = [
        t
        for t in client_hits[client]
        if now - t < WINDOW
    ]

    client_hits[client] = hits

    if len(hits) >= RATE_LIMIT:

        retry = max(
            1,
            int(WINDOW - (now - hits[0])) + 1
        )

        response = JSONResponse(
            status_code=429,
            content={
                "detail": "Rate limit exceeded"
            },
        )

        response.headers["Retry-After"] = str(retry)
        response.headers["X-Request-ID"] = getattr(
            request.state,
            "request_id",
            str(uuid.uuid4())
        )

        return response

    hits.append(now)

    client_hits[client] = hits

    return await call_next(request)


# ----------------------------
# Ping Endpoint
# ----------------------------
@app.get("/ping")
async def ping(request: Request):
    return {
        "email": "23f1000212@ds.study.iitm.ac.in",
        "request_id": request.state.request_id,
    }
