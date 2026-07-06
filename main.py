from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uuid
import time
from collections import defaultdict

app = FastAPI()

# ==========================================
# 🛑 IMPORTANT: UPDATE THESE TWO VARIABLES
# ==========================================
MY_EMAIL = "23f1000212@ds.study.iitm.ac.in" # 1. Put your logged-in email here

# 2. Add the exact base URL of your exam portal (e.g., "https://exam.domain.com")
# If you don't add this, your browser will block the exam page's verification requests.
EXAM_PAGE_ORIGIN = "https://exam.sanand.workers.dev" 
# ==========================================

# --- Middleware 2: CORS ---
# CORSMiddleware handles OPTIONS preflights and ACAO headers. 
# It strictly blocks ACAO headers for unlisted origins (no wildcards).
# --- Middleware 2: CORS ---
ALLOWED_ORIGINS = [
    "https://app-ah3n9p.example.com",
    EXAM_PAGE_ORIGIN
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"]  # 👈 Add this line!
)

# In-memory database for Rate Limiting: { "client_id": [timestamp1, timestamp2, ...] }
rate_limit_db = defaultdict(list)
RATE_LIMIT_MAX = 12
RATE_LIMIT_WINDOW_SEC = 10

# --- Middleware 1 & 3: Rate Limiting & Request Context ---
@app.middleware("http")
async def custom_stack_middleware(request: Request, call_next):
    # 1. RATE LIMITING (Middleware 3)
    # We ignore OPTIONS requests as they are CORS preflights.
    if request.method != "OPTIONS":
        client_id = request.headers.get("X-Client-Id")
        if client_id:
            current_time = time.time()
            
            # Filter timestamps to only keep ones within the last 10 seconds
            active_timestamps = [
                ts for ts in rate_limit_db[client_id] 
                if current_time - ts < RATE_LIMIT_WINDOW_SEC
            ]
            
            # If they hit 12 requests, block with HTTP 429
            if len(active_timestamps) >= RATE_LIMIT_MAX:
                rate_limit_db[client_id] = active_timestamps # Keep state clean
                return JSONResponse(status_code=429, content={"detail": "Too Many Requests"})
            
            # Otherwise, record this request's timestamp
            active_timestamps.append(current_time)
            rate_limit_db[client_id] = active_timestamps

    # 2. REQUEST CONTEXT (Middleware 1)
    # Extract existing ID or generate a new UUID4
    request_id = request.headers.get("X-Request-ID")
    if not request_id:
        request_id = str(uuid.uuid4())

    # Store it in request.state so the route endpoint can access it
    request.state.request_id = request_id

    # Execute the request (hits the /ping endpoint)
    response = await call_next(request)

    # Attach the request ID to the outgoing response header
    response.headers["X-Request-ID"] = request_id
    return response

# --- Endpoint ---
@app.get("/ping")
async def ping(request: Request):
    return {
        "email": MY_EMAIL,
        "request_id": request.state.request_id
    }
