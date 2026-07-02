import time
import uuid
from collections import defaultdict, deque

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

EMAIL = "23f1000212@ds.study.iitm.ac.in"

ALLOWED_ORIGINS = [
    "https://app-ah3n9p.example.com",
    "https://exam.sanand.workers.dev",
]

RATE_LIMIT = 12
WINDOW = 10

app = FastAPI(title="Middleware Stack API")

# ----------------------------------------------------
# CORS
# ----------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

# ----------------------------------------------------
# Rate Limit Storage
# ----------------------------------------------------

client_buckets = defaultdict(deque)

# ----------------------------------------------------
# Middleware
# ----------------------------------------------------

@app.middleware("http")
async def middleware(request: Request, call_next):

    # -------------------------
    # Request Context
    # -------------------------

    request_id = request.headers.get("x-request-id")

    if not request_id:
        request_id = str(uuid.uuid4())

    request.state.request_id = request_id

    # -------------------------
    # Rate Limiter
    # -------------------------

    if request.method != "OPTIONS":

        client_id = request.headers.get("x-client-id", "default")

        now = time.time()

        bucket = client_buckets[client_id]

        while bucket and now - bucket[0] >= WINDOW:
            bucket.popleft()

        if len(bucket) >= RATE_LIMIT:

            response = JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded"
                },
            )

            response.headers["Retry-After"] = "10"
            response.headers["X-Request-ID"] = request_id

            return response

        bucket.append(now)

    response = await call_next(request)

    response.headers["X-Request-ID"] = request_id

    return response

# ----------------------------------------------------
# Root
# ----------------------------------------------------

@app.get("/")
def root():
    return {
        "message": "Middleware Stack API Running"
    }

# ----------------------------------------------------
# Ping
# ----------------------------------------------------

@app.get("/ping")
def ping(request: Request):
    return {
        "email": EMAIL,
        "request_id": request.state.request_id
    }
