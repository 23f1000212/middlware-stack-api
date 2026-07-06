import time
import uuid
from collections import defaultdict

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# ==========================================
EMAIL = "23f1000212@ds.study.iitm.ac.in"
EXAM_PAGE_ORIGIN = "https://exam.sanand.workers.dev"
ASSIGNED_ORIGIN = "https://app-ah3n9p.example.com"
# ==========================================

# STRICT CORS (No wildcards per instructions)
ALLOWED_ORIGINS = [
    ASSIGNED_ORIGIN,
    EXAM_PAGE_ORIGIN
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "Retry-After"]
)

RATE_LIMIT = 12
WINDOW = 10
client_hits = defaultdict(list)

# ----------------------------
# Combined Middleware
# ----------------------------
@app.middleware("http")
async def combined_stack_middleware(request: Request, call_next):
    # 1. Ensure Request ID exists immediately
    request_id = request.headers.get("X-Request-ID")
    if not request_id:
        request_id = str(uuid.uuid4())
    
    request.state.request_id = request_id

    # 2. Rate Limiting (Ignore CORS preflights)
    if request.method != "OPTIONS":
        client_id = request.headers.get("X-Client-Id")
        if client_id:
            now = time.time()
            # Filter hits inside the 10s window
            hits = [t for t in client_hits[client_id] if now - t < WINDOW]
            
            # Check limit
            if len(hits) >= RATE_LIMIT:
                client_hits[client_id] = hits
                retry = max(1, int(WINDOW - (now - hits[0])) + 1)
                
                # Early return for 429
                response = JSONResponse(
                    status_code=429,
                    content={"detail": "Too Many Requests"}
                )
                response.headers["Retry-After"] = str(retry)
                response.headers["X-Request-ID"] = request_id  # Attach header to early exit
                return response
            
            # Record hit
            hits.append(now)
            client_hits[client_id] = hits

    # 3. Proceed to endpoint
    response = await call_next(request)

    # 4. Attach header to normal exit
    response.headers["X-Request-ID"] = request_id
    return response

# ----------------------------
# Ping Endpoint
# ----------------------------
@app.get("/ping")
async def ping(request: Request):
    return {
        "email": EMAIL,
        "request_id": request.state.request_id,
    }
